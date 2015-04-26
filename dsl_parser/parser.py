########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


import collections
import copy
import contextlib
import urllib2

import yaml
import yaml.parser

from dsl_parser import (constants,
                        utils,
                        functions)
from dsl_parser.interfaces import interfaces_parser
from dsl_parser.exceptions import (DSLParsingFormatException,
                                   DSLParsingLogicException)


NODE_TEMPLATES = 'node_templates'
IMPORTS = 'imports'
NODE_TYPES = 'node_types'
PLUGINS = 'plugins'
INTERFACES = 'interfaces'
SOURCE_INTERFACES = 'source_interfaces'
TARGET_INTERFACES = 'target_interfaces'
WORKFLOWS = 'workflows'
RELATIONSHIPS = 'relationships'
PROPERTIES = 'properties'
PARAMETERS = 'parameters'
TYPE_HIERARCHY = 'type_hierarchy'
POLICY_TRIGGERS = 'policy_triggers'
POLICY_TYPES = 'policy_types'
GROUPS = 'groups'
INPUTS = 'inputs'
OUTPUTS = 'outputs'

HOST_TYPE = 'cloudify.nodes.Compute'
DEPENDS_ON_REL_TYPE = 'cloudify.relationships.depends_on'
CONTAINED_IN_REL_TYPE = 'cloudify.relationships.contained_in'
CONNECTED_TO_REL_TYPE = 'cloudify.relationships.connected_to'
OpDescriptor = collections.namedtuple('OpDescriptor', [
    'plugin', 'op_struct', 'name'])


def parse_from_path(dsl_file_path, resources_base_url=None):
    with open(dsl_file_path, 'r') as f:
        dsl_string = f.read()
    return _parse(dsl_string, resources_base_url, dsl_file_path)


def parse_from_url(dsl_url, resources_base_url=None):
    try:
        with contextlib.closing(urllib2.urlopen(dsl_url)) as f:
            dsl_string = f.read()
    except urllib2.HTTPError as e:
        if e.code == 404:
            # HTTPError.__str__ uses the 'msg'.
            # by default it is set to 'Not Found' for 404 errors, which is not
            # very helpful, so we override it with a more meaningful message
            # that specifies the missing url.
            e.msg = '{0} not found'.format(e.filename)
        raise
    return _parse(dsl_string, resources_base_url, dsl_url)


def parse(dsl_string, resources_base_url=None):
    return _parse(dsl_string, resources_base_url)


def _parse(dsl_string, resources_base_url, dsl_location=None):
    from dsl_parser.elements.parser import Parser
    from dsl_parser.elements import blueprint

    parsed_dsl = _load_yaml(dsl_string, 'Failed to parse DSL')

    parser = Parser()

    # validate and extract version
    parser.parse(parsed_dsl,
                 element_cls=blueprint.BlueprintVersionExtractor,
                 strict=False)

    # handle imports
    result = parser.parse(
        value=parsed_dsl,
        inputs={
            'main_blueprint': parsed_dsl,
            'resources_base_url': resources_base_url,
            'blueprint_location': dsl_location
        },
        element_cls=blueprint.BlueprintImporter,
        strict=False)
    resource_base = result['resource_base']
    merged_blueprint = result['merged_blueprint']

    # parse blueprint
    plan = parser.parse(
        value=merged_blueprint,
        inputs={
            'resource_base': resource_base
        },
        element_cls=blueprint.Blueprint)

    functions.validate_functions(plan)
    return plan


def _post_process_nodes(processed_nodes,
                        types,
                        relationships,
                        plugins,
                        resource_base):
    node_name_to_node = dict((node['id'], node) for node in processed_nodes)

    # handle plugins and operations for all nodes
    for node in processed_nodes:
        node_type = types[node['type']]
        interfaces = interfaces_parser.merge_node_type_and_node_template_interfaces(  # noqa
            node_type=node_type,
            node_template=node)

        # handle plugins and operations
        partial_error_message = 'in node {0} of type {1}' \
            .format(node['id'], node['type'])
        operations = _process_context_operations(
            partial_error_message=partial_error_message,
            interfaces=interfaces,
            plugins=plugins,
            node=node,
            error_code=10,
            resource_base=resource_base)
        node['operations'] = operations

    depends_on_rel_types = _build_family_descendants_set(
        relationships, DEPENDS_ON_REL_TYPE)
    contained_in_rel_types = _build_family_descendants_set(
        relationships, CONTAINED_IN_REL_TYPE)
    connected_to_rel_types = _build_family_descendants_set(
        relationships, CONNECTED_TO_REL_TYPE)
    for node in processed_nodes:
        _post_process_node_relationships(node,
                                         node_name_to_node,
                                         plugins,
                                         contained_in_rel_types,
                                         connected_to_rel_types,
                                         depends_on_rel_types,
                                         relationships,
                                         resource_base)
        node[TYPE_HIERARCHY] = _create_type_hierarchy(node['type'], types)

    # set host_id property to all relevant nodes
    host_types = _build_family_descendants_set(types, HOST_TYPE)
    for node in processed_nodes:
        host_id = _extract_node_host_id(node, node_name_to_node, host_types,
                                        contained_in_rel_types)
        if host_id:
            node['host_id'] = host_id

    for node in processed_nodes:
        # fix plugins for all nodes
        node[PLUGINS] = _get_plugins_from_operations(node, plugins)

    # set plugins_to_install property for nodes
    for node in processed_nodes:
        if node['type'] in host_types:
            plugins_to_install = {}
            for another_node in processed_nodes:
                # going over all other nodes, to accumulate plugins
                # from different nodes whose host is the current node
                if another_node.get('host_id') == node['id'] \
                        and PLUGINS in another_node:
                    # ok to override here since we assume it is the same plugin
                    for plugin in another_node[PLUGINS]:
                        if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                                == constants.HOST_AGENT:
                            plugin_name = plugin['name']
                            plugins_to_install[plugin_name] = plugin
            node['plugins_to_install'] = plugins_to_install.values()

    # set deployment_plugins_to_install property for nodes
    for node in processed_nodes:
        deployment_plugins_to_install = {}
        for plugin in node[PLUGINS]:
            if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                    == constants.CENTRAL_DEPLOYMENT_AGENT:
                plugin_name = plugin['name']
                deployment_plugins_to_install[plugin_name] = plugin
        node[constants.DEPLOYMENT_PLUGINS_TO_INSTALL] = \
            deployment_plugins_to_install.values()

    _validate_agent_plugins_on_host_nodes(processed_nodes)


def _create_type_hierarchy(type_name, types):
    """
    Creates node types hierarchy as list where the last type in the list is
    the actual node type.
    """
    current_type = types[type_name]
    if 'derived_from' in current_type:
        parent_type_name = current_type['derived_from']
        types_hierarchy = _create_type_hierarchy(parent_type_name, types)
        types_hierarchy.append(type_name)
        return types_hierarchy
    return [type_name]


def _post_process_node_relationships(processed_node,
                                     node_name_to_node,
                                     plugins,
                                     contained_in_rel_types,
                                     connected_to_rel_types,
                                     depends_on_rel_type,
                                     relationships,
                                     resource_base):
    contained_in_relationships = []
    if RELATIONSHIPS in processed_node:
        for relationship in processed_node[RELATIONSHIPS]:
            target_node = node_name_to_node[relationship['target_id']]
            _process_node_relationships_operations(
                relationship, 'source_interfaces', 'source_operations',
                processed_node, plugins, resource_base)
            _process_node_relationships_operations(
                relationship, 'target_interfaces', 'target_operations',
                target_node, plugins, resource_base)
            _add_base_type_to_relationship(relationship,
                                           contained_in_rel_types,
                                           connected_to_rel_types,
                                           depends_on_rel_type,
                                           contained_in_relationships)
            relationship[TYPE_HIERARCHY] = _create_type_hierarchy(
                relationship['type'], relationships)

    if len(contained_in_relationships) > 1:
        ex = DSLParsingLogicException(
            112, 'Node {0} has more than one relationship that is derived'
                 ' from {1} relationship. Found: {2}'
                 .format(processed_node['name'],
                         CONTAINED_IN_REL_TYPE,
                         contained_in_relationships))
        ex.relationship_types = contained_in_relationships
        raise ex


# used in multi_instance
def _add_base_type_to_relationship(relationship,
                                   contained_in_rel_types,
                                   connected_to_rel_types,
                                   depends_on_rel_types,
                                   contained_in_relationships):
    base = 'undefined'
    rel_type = relationship['type']
    if rel_type in contained_in_rel_types:
        base = 'contained'
        contained_in_relationships.append(rel_type)
    elif rel_type in connected_to_rel_types:
        base = 'connected'
    elif rel_type in depends_on_rel_types:
        base = 'depends'
    relationship['base'] = base


def _process_context_operations(partial_error_message,
                                interfaces, plugins,
                                node,
                                error_code,
                                resource_base):
    operations = {}
    for interface_name, interface in interfaces.items():
        operation_mapping_context = \
            _extract_plugin_names_and_operation_mapping_from_interface(
                interface,
                plugins,
                error_code,
                'In interface {0} {1}'.format(interface_name,
                                              partial_error_message),
                resource_base)
        for op_descriptor in operation_mapping_context:
            op_struct = op_descriptor.op_struct
            plugin_name = op_descriptor.op_struct['plugin']
            operation_name = op_descriptor.name
            if op_descriptor.plugin:
                node[PLUGINS][plugin_name] = op_descriptor.plugin
            op_struct = op_struct.copy()
            if operation_name in operations:
                # Indicate this implicit operation name needs to be
                # removed as we can only
                # support explicit implementation in this case
                operations[operation_name] = None
            else:
                operations[operation_name] = op_struct
            operations['{0}.{1}'.format(interface_name,
                                        operation_name)] = op_struct

    return dict((operation, op_struct) for operation, op_struct in
                operations.iteritems() if op_struct is not None)


def _process_node_relationships_operations(relationship,
                                           interfaces_attribute,
                                           operations_attribute,
                                           node_for_plugins,
                                           plugins,
                                           resource_base):
    if interfaces_attribute in relationship:
        partial_error_message = 'in relationship of type {0} in node {1}'\
                                .format(relationship['type'],
                                        node_for_plugins['id'])

        operations = _process_context_operations(
            partial_error_message,
            relationship[interfaces_attribute],
            plugins, node_for_plugins, 19, resource_base)

        relationship[operations_attribute] = operations


def _extract_plugin_names_and_operation_mapping_from_interface(
        interface,
        plugins,
        error_code,
        partial_error_message,
        resource_base):
    result = []
    for operation_name, operation_content in interface.items():
        op_descriptor = \
            _extract_plugin_name_and_operation_mapping_from_operation(
                plugins,
                operation_name,
                operation_content,
                error_code,
                partial_error_message,
                resource_base)
        result.append(op_descriptor)
    return result


def _validate_relationship_fields(rel_obj, plugins, rel_name, resource_base):
    for interfaces in [SOURCE_INTERFACES, TARGET_INTERFACES]:
        if interfaces in rel_obj:
            for interface_name, interface in rel_obj[interfaces].items():
                _extract_plugin_names_and_operation_mapping_from_interface(
                    interface,
                    plugins,
                    19,
                    'Relationship: {0}'.format(rel_name),
                    resource_base=resource_base)


def _validate_agent_plugins_on_host_nodes(processed_nodes):
    for node in processed_nodes:
        if 'host_id' not in node and PLUGINS in node:
            for plugin in node[PLUGINS]:
                if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                        == constants.HOST_AGENT:
                    raise DSLParsingLogicException(
                        24, "node {0} has no relationship which makes it "
                            "contained within a host and it has a "
                            "plugin[{1}] with '{2}' as an executor. "
                            "These types of plugins must be "
                            "installed on a host".format(node['id'],
                                                         plugin['name'],
                                                         constants.HOST_AGENT))


def _build_family_descendants_set(types_dict, derived_from):
    return set(type_name for type_name in types_dict.iterkeys()
               if _is_derived_from(type_name, types_dict, derived_from))


def _is_derived_from(type_name, types, derived_from):
    if type_name == derived_from:
        return True
    elif 'derived_from' in types[type_name]:
        return _is_derived_from(types[type_name]['derived_from'], types,
                                derived_from)
    return False


def _relationship_type_merging_function(overridden_relationship_type,
                                        overriding_relationship_type):

    merged_type = overriding_relationship_type

    merged_props = utils.merge_sub_dicts(overridden_relationship_type,
                                         merged_type,
                                         PROPERTIES)

    merged_type[PROPERTIES] = merged_props

    # derived source and target interfaces
    merged_interfaces = \
        interfaces_parser.merge_relationship_type_interfaces(
            overridden_relationship_type=overridden_relationship_type,
            overriding_relationship_type=merged_type
        )
    merged_type[SOURCE_INTERFACES] = merged_interfaces[SOURCE_INTERFACES]
    merged_type[TARGET_INTERFACES] = merged_interfaces[TARGET_INTERFACES]

    return merged_type


def _node_type_interfaces_merging_function(overridden_node_type,
                                           overriding_node_type):

    merged_type = overriding_node_type

    # derive properties
    merged_type[PROPERTIES] = utils.merge_sub_dicts(
        overridden_node_type,
        merged_type,
        PROPERTIES)

    # derive interfaces
    merged_type[INTERFACES] = interfaces_parser.merge_node_type_interfaces(
        overridden_node_type=overridden_node_type,
        overriding_node_type=overriding_node_type
    )

    return merged_type


def _extract_complete_relationship_type(relationship_types,
                                        relationship_type_name,
                                        relationship_type):
    return utils.extract_complete_type_recursive(
        dsl_type_name=relationship_type_name,
        dsl_type=relationship_type,
        dsl_container=relationship_types,
        is_relationships=True,
        merging_func=_relationship_type_merging_function
    )


def _extract_complete_node_type(node_types,
                                node_type_name,
                                node_type):
    return utils.extract_complete_type_recursive(
        dsl_type_name=node_type_name,
        dsl_type=node_type,
        dsl_container=node_types,
        is_relationships=False,
        merging_func=_node_type_interfaces_merging_function
    )


def _extract_plugin_name_and_operation_mapping_from_operation(
        plugins,
        operation_name,
        operation_content,
        error_code,
        partial_error_message,
        resource_base,
        is_workflows=False):
    payload_field_name = 'parameters' if is_workflows else 'inputs'
    mapping_field_name = 'mapping' if is_workflows else 'implementation'
    operation_payload = {}
    operation_executor = None
    operation_max_retries = None
    operation_retry_interval = None
    if isinstance(operation_content, basestring):
        operation_mapping = operation_content
    else:
        # top level types do not undergo proper merge
        operation_mapping = operation_content.get(
            mapping_field_name, '')
        operation_payload = operation_content.get(
            payload_field_name, {})
        operation_executor = operation_content.get(
            'executor', None)
        operation_max_retries = operation_content.get(
            'max_retries', None)
        operation_retry_interval = operation_content.get(
            'retry_interval', None)

    if not operation_mapping:
        if is_workflows:
            operation_struct = _workflow_operation_struct(
                plugin_name='',
                workflow_mapping='',
                workflow_parameters={}
            )
        else:
            operation_struct = _operation_struct(
                plugin_name='',
                operation_mapping='',
                operation_inputs={},
                executor=None,
                max_retries=None,
                retry_interval=None
            )
        return OpDescriptor(name=operation_name,
                            plugin='',
                            op_struct=operation_struct)

    longest_prefix = 0
    longest_prefix_plugin_name = None
    for plugin_name in plugins.keys():
        if operation_mapping.startswith('{0}.'.format(plugin_name)):
            plugin_name_length = len(plugin_name)
            if plugin_name_length > longest_prefix:
                longest_prefix = plugin_name_length
                longest_prefix_plugin_name = plugin_name
    if longest_prefix_plugin_name is not None:

        if is_workflows:
            operation_struct = _workflow_operation_struct(
                plugin_name=longest_prefix_plugin_name,
                workflow_mapping=operation_mapping[longest_prefix + 1:],
                workflow_parameters=operation_payload
            )
        else:
            operation_struct = _operation_struct(
                plugin_name=longest_prefix_plugin_name,
                operation_mapping=operation_mapping[longest_prefix + 1:],
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval
            )

        return OpDescriptor(
            name=operation_name,
            plugin=plugins[longest_prefix_plugin_name],
            op_struct=operation_struct)
    elif resource_base and _resource_exists(resource_base, operation_mapping):
        operation_payload = copy.deepcopy(operation_payload or {})
        if constants.SCRIPT_PATH_PROPERTY in operation_payload:
            message = 'Cannot define {0} property in {1} for {2} "{3}"' \
                .format(constants.SCRIPT_PATH_PROPERTY,
                        operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise DSLParsingLogicException(60, message)
        script_path = operation_mapping
        if is_workflows:
            operation_mapping = constants.SCRIPT_PLUGIN_EXECUTE_WORKFLOW_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: {
                    'default': script_path,
                    'description': 'Workflow script executed by the script'
                                   ' plugin'
                }
            })
        else:
            operation_mapping = constants.SCRIPT_PLUGIN_RUN_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: script_path
            })
        if constants.SCRIPT_PLUGIN_NAME not in plugins:
            message = 'Script plugin is not defined but it is required for' \
                      ' mapping: {0} of {1} "{2}"' \
                .format(operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise DSLParsingLogicException(61, message)

        if is_workflows:
            operation_struct = _workflow_operation_struct(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                workflow_mapping=operation_mapping,
                workflow_parameters=operation_payload
            )
        else:
            operation_struct = _operation_struct(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                operation_mapping=operation_mapping,
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval
            )

        return OpDescriptor(
            name=operation_name,
            plugin=plugins[constants.SCRIPT_PLUGIN_NAME],
            op_struct=operation_struct)
    else:
        # This is an error for validation done somewhere down the
        # current stack trace
        base_error_message = 'Could not extract plugin from {2} ' \
                             'mapping {0}, which is declared for {2} ' \
                             '{1}.'.format(
                                 operation_mapping,
                                 operation_name,
                                 'workflow' if is_workflows else 'operation')
        error_message = base_error_message + partial_error_message
        raise DSLParsingLogicException(error_code, error_message)


def _resource_exists(resource_base, resource_name):
    return _validate_url_exists('{0}/{1}'.format(resource_base, resource_name))


def _process_node_relationship(relationship,
                               relationship_types):
    relationship_type = relationship_types[relationship['type']]
    source_and_target_interfaces = \
        interfaces_parser.\
        merge_relationship_type_and_instance_interfaces(
            relationship_type=relationship_type,
            relationship_instance=relationship
        )
    source_interfaces = source_and_target_interfaces[SOURCE_INTERFACES]
    relationship[SOURCE_INTERFACES] = source_interfaces
    target_interfaces = source_and_target_interfaces[TARGET_INTERFACES]
    relationship[TARGET_INTERFACES] = target_interfaces
    relationship['target_id'] = relationship['target']
    del (relationship['target'])
    relationship['state'] = 'reachable'
    return relationship


def _operation_struct(plugin_name,
                      operation_mapping,
                      operation_inputs,
                      executor,
                      max_retries,
                      retry_interval):
    return {
        'plugin': plugin_name,
        'operation': operation_mapping,
        'executor': executor,
        'inputs': operation_inputs,
        'has_intrinsic_functions': False,
        'max_retries': max_retries,
        'retry_interval': retry_interval
    }


def _workflow_operation_struct(plugin_name,
                               workflow_mapping,
                               workflow_parameters):
    return {
        'plugin': plugin_name,
        'operation': workflow_mapping,
        'parameters': workflow_parameters
    }


def _extract_node_host_id(processed_node,
                          node_name_to_node,
                          host_types,
                          contained_in_rel_types):
    if processed_node['type'] in host_types:
        return processed_node['id']
    else:
        if RELATIONSHIPS in processed_node:
            for rel in processed_node[RELATIONSHIPS]:
                if rel['type'] in contained_in_rel_types:
                    return _extract_node_host_id(
                        node_name_to_node[rel['target_id']],
                        node_name_to_node,
                        host_types,
                        contained_in_rel_types)


def _load_yaml(yaml_stream, error_message):
    try:
        # load of empty string returns None so we convert it to an empty dict
        return yaml.safe_load(yaml_stream) or {}
    except yaml.parser.ParserError, ex:
        raise DSLParsingFormatException(-1, '{0}: Illegal yaml; {1}'
                                        .format(error_message, ex))


def _validate_url_exists(url):
    try:
        with contextlib.closing(urllib2.urlopen(url)):
            return True
    except urllib2.URLError:
        return False


def _get_plugins_from_operations(node, processed_plugins):
    added_plugins = set()
    plugins = []
    node_operations = node.get('operations', {})
    plugins_from_operations = _get_plugins_from_operations_helper(
        node_operations, processed_plugins)
    _add_plugins(plugins, plugins_from_operations, added_plugins)
    plugins_from_node = node.get('plugins', {}).values()
    _add_plugins(plugins, plugins_from_node, added_plugins)
    for relationship in node.get('relationships', []):
        source_operations = relationship.get('source_operations', {})
        target_operations = relationship.get('target_operations', {})
        _set_operations_executor(target_operations, processed_plugins)
        _set_operations_executor(source_operations, processed_plugins)
    return plugins


def _add_plugins(plugins, new_plugins, added_plugins):
    for plugin in new_plugins:
        plugin_key = (plugin['name'], plugin['executor'])
        if plugin_key not in added_plugins:
            plugins.append(plugin)
            added_plugins.add(plugin_key)


def _get_plugins_from_operations_helper(operations, processed_plugins):
    plugins = []
    for operation in operations.values():
        real_executor = _set_operation_executor(
            operation, processed_plugins)
        plugin_name = operation['plugin']
        if not plugin_name:
            # no-op
            continue
        plugin = copy.deepcopy(processed_plugins[plugin_name])
        plugin['executor'] = real_executor
        plugins.append(plugin)
    return plugins


def _set_operations_executor(operations, processed_plugins):
    for operation in operations.values():
        _set_operation_executor(operation, processed_plugins)


def _set_operation_executor(operation, processed_plugins):
    operation_executor = operation['executor']
    plugin_name = operation['plugin']
    if not plugin_name:
        # no-op
        return
    if operation_executor is None:
        real_executor = processed_plugins[plugin_name]['executor']
    else:
        real_executor = operation_executor

    # set actual executor for the operation
    operation['executor'] = real_executor

    return real_executor
