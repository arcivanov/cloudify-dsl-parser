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
import os
import copy
import contextlib
import urllib
import urllib2

import jsonschema
import yaml
import yaml.parser

from dsl_parser import (constants,
                        functions,
                        models,
                        schemas,
                        utils,
                        version)
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

parse_context = models.ParseContext()


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
    try:
        parsed_dsl = _load_yaml(dsl_string, 'Failed to parse DSL')

        # not sure about the name. this will actually be the dsl_location
        # minus the /blueprint.yaml at the end of it
        resource_base = None
        if dsl_location:
            dsl_location = _dsl_location_to_url(dsl_location,
                                                resources_base_url)
            resource_base = dsl_location[:dsl_location.rfind('/')]
        combined_parsed_dsl = _combine_imports(parsed_dsl,
                                               dsl_location,
                                               resources_base_url)

        _validate_dsl_schema(combined_parsed_dsl)

        dsl_version = combined_parsed_dsl[version.VERSION]
        version.validate_dsl_version(dsl_version)
        parsed_dsl_version = version.parse_dsl_version(dsl_version)
        parse_context.version = parsed_dsl_version

        nodes = combined_parsed_dsl[NODE_TEMPLATES]
        node_names_set = set(nodes.keys())

        top_level_relationships = _process_relationships(
            combined_parsed_dsl, resource_base)

        plugins = combined_parsed_dsl.get(PLUGINS, {})
        processed_plugins = dict((name, _process_plugin(plugin, name,
                                                        dsl_version))
                                 for (name, plugin) in plugins.items())

        processed_nodes = [_process_node(node_name,
                                         node,
                                         combined_parsed_dsl,
                                         top_level_relationships,
                                         node_names_set,
                                         processed_plugins,
                                         resource_base)
                           for node_name, node in nodes.iteritems()]

        _post_process_nodes(processed_nodes,
                            combined_parsed_dsl.get(NODE_TYPES, {}),
                            combined_parsed_dsl.get(RELATIONSHIPS, {}),
                            processed_plugins,
                            resource_base)

        inputs = combined_parsed_dsl.get(INPUTS, {})
        outputs = combined_parsed_dsl.get(OUTPUTS, {})

        processed_workflows = _process_workflows(
            combined_parsed_dsl.get(WORKFLOWS, {}),
            processed_plugins,
            resource_base)
        workflow_plugins_to_install = _create_plan_workflow_plugins(
            processed_workflows,
            processed_plugins)

        plan_deployment_plugins = _create_plan_deployment_plugins(
            processed_nodes)

        policy_types = _process_policy_types(
            combined_parsed_dsl.get(POLICY_TYPES, {}))

        policy_triggers = _process_policy_triggers(
            combined_parsed_dsl.get(POLICY_TRIGGERS, {}))

        groups = _process_groups(
            combined_parsed_dsl.get(GROUPS, {}),
            policy_types,
            policy_triggers,
            processed_nodes)

        plan = models.Plan({
            constants.NODES: processed_nodes,
            RELATIONSHIPS: top_level_relationships,
            WORKFLOWS: processed_workflows,
            POLICY_TYPES: policy_types,
            POLICY_TRIGGERS: policy_triggers,
            GROUPS: groups,
            INPUTS: inputs,
            OUTPUTS: outputs,
            constants.DEPLOYMENT_PLUGINS_TO_INSTALL: plan_deployment_plugins,
            constants.WORKFLOW_PLUGINS_TO_INSTALL: workflow_plugins_to_install,
            'version': version.process_dsl_version(dsl_version)
        })

        functions.validate_functions(plan)

        return plan
    finally:
        parse_context.clear()


def _post_process_nodes(processed_nodes,
                        types,
                        relationships,
                        plugins,
                        resource_base):
    node_name_to_node = dict((node['id'], node) for node in processed_nodes)

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
        node[PLUGINS] = get_plugins_from_operations(node, plugins)

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


def _create_plan_deployment_plugins(processed_nodes):
    deployment_plugins = []
    deployment_plugin_names = set()
    for node in processed_nodes:
        if constants.DEPLOYMENT_PLUGINS_TO_INSTALL in node:
            for deployment_plugin in \
                    node[constants.DEPLOYMENT_PLUGINS_TO_INSTALL]:
                if deployment_plugin[constants.PLUGIN_NAME_KEY] \
                        not in deployment_plugin_names:
                    deployment_plugins.append(deployment_plugin)
                    deployment_plugin_names \
                        .add(deployment_plugin[constants.PLUGIN_NAME_KEY])
    return deployment_plugins


def _create_plan_workflow_plugins(workflows, plugins):
    workflow_plugins = []
    workflow_plugin_names = set()
    for workflow, op_struct in workflows.items():
        if op_struct['plugin'] not in workflow_plugin_names:
            plugin_name = op_struct['plugin']
            workflow_plugins.append(plugins[plugin_name])
            workflow_plugin_names.add(plugin_name)
    return workflow_plugins


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
    plugin_names = plugins.keys()
    result = []
    for operation_name, operation_content in interface.items():
        op_descriptor = \
            _extract_plugin_name_and_operation_mapping_from_operation(
                plugins,
                plugin_names,
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


def relationship_type_merging_function(overridden_relationship_type,
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


def node_type_interfaces_merging_function(overridden_node_type,
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


def extract_complete_relationship_type(relationship_types,
                                       relationship_type_name,
                                       relationship_type):

    if 'derived_from' not in relationship_type:
        # top level types do not undergo merge properly,
        # which means the operations are not augmented.
        # do so here
        source_interfaces = relationship_type.get('source_interfaces', {})
        for interface_name, interface in source_interfaces.iteritems():
            for operation_name, operation in interface.iteritems():
                augment_operation(operation)
        target_interfaces = relationship_type.get('target_interfaces', {})
        for interface_name, interface in target_interfaces.iteritems():
            for operation_name, operation in interface.iteritems():
                augment_operation(operation)

    return utils.extract_complete_type_recursive(
        dsl_type_name=relationship_type_name,
        dsl_type=relationship_type,
        dsl_container=relationship_types,
        is_relationships=True,
        merging_func=relationship_type_merging_function
    )


def extract_complete_node_type(node_types,
                               node_type_name,
                               node_type):

    if 'derived_from' not in node_type:
        # top level types do not undergo merge properly,
        # which means the operations are not augmented.
        # do so here
        interfaces = node_type.get('interfaces', {})
        for interface_name, interface in interfaces.iteritems():
            for operation_name, operation in interface.iteritems():
                augment_operation(operation)

    return utils.extract_complete_type_recursive(
        dsl_type_name=node_type_name,
        dsl_type=node_type,
        dsl_container=node_types,
        is_relationships=False,
        merging_func=node_type_interfaces_merging_function
    )


def augment_operation(operation):
    if isinstance(operation, str):
        operation = {
            'implementation': operation
        }
    if 'executor' not in operation:
        operation['executor'] = None
    if 'implementation' not in operation:
        operation['implementation'] = ''
    if 'inputs' not in operation:
        operation['inputs'] = {}
    if 'max_retries' not in operation:
        operation['max_retries'] = None
    if 'retry_interval' not in operation:
        operation['retry_interval'] = None


def _process_relationships(combined_parsed_dsl, resource_base):
    processed_relationships = {}
    if RELATIONSHIPS not in combined_parsed_dsl:
        return processed_relationships

    relationship_types = combined_parsed_dsl[RELATIONSHIPS]

    for relationship_type_name, relationship_type in \
            relationship_types.iteritems():
        complete_relationship = extract_complete_relationship_type(
            relationship_type=relationship_type,
            relationship_type_name=relationship_type_name,
            relationship_types=relationship_types
        )

        plugins = combined_parsed_dsl.get(PLUGINS, {})
        _validate_relationship_fields(relationship_type, plugins,
                                      relationship_type_name,
                                      resource_base)
        complete_rel_obj_copy = copy.deepcopy(complete_relationship)
        processed_relationships[relationship_type_name] = \
            complete_rel_obj_copy
        processed_relationships[relationship_type_name]['name'] = \
            relationship_type_name
    return processed_relationships


def _extract_plugin_name_and_operation_mapping_from_operation(
        plugins,
        plugin_names,
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

    if not version.is_version_equal_or_greater_than(
            parse_context.version,
            version.parse_dsl_version(version.DSL_VERSION_1_1)):
        def error_message(field):
            return (
                'Cannot use {0} with {1} in operation {2}. '
                '{3}.'.format(field,
                              parse_context.version,
                              operation_name,
                              partial_error_message))
        if operation_max_retries:
            raise DSLParsingLogicException(81, error_message('max_retries'))
        if operation_retry_interval:
            raise DSLParsingLogicException(81, error_message('retry_interval'))

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
    for plugin_name in plugin_names:
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


def _process_workflows(workflows, plugins, resource_base):
    processed_workflows = {}
    plugin_names = plugins.keys()
    for name, mapping in workflows.items():
        op_descriptor = \
            _extract_plugin_name_and_operation_mapping_from_operation(
                plugins=plugins,
                plugin_names=plugin_names,
                operation_name=name,
                operation_content=mapping,
                error_code=21,
                partial_error_message='',
                resource_base=resource_base,
                is_workflows=True)
        processed_workflows[name] = op_descriptor.op_struct
    return processed_workflows


def _process_policy_types(policy_types):
    processed = copy.deepcopy(policy_types)
    for policy in processed.values():
        policy[PROPERTIES] = policy.get(PROPERTIES, {})
    return processed


def _process_policy_triggers(policy_triggers):
    processed = copy.deepcopy(policy_triggers)
    for trigger in processed.values():
        trigger[PARAMETERS] = trigger.get(PARAMETERS, {})
    return processed


def _process_groups(groups, policy_types, policy_triggers, processed_nodes):
    node_names = set(n['name'] for n in processed_nodes)
    processed_groups = copy.deepcopy(groups)
    for group_name, group in processed_groups.items():
        for member in group['members']:
            if member not in node_names:
                raise DSLParsingLogicException(
                    40,
                    'member "{0}" of group "{1}" does not '
                    'match any defined node'.format(member, groups))
        for policy_name, policy in group['policies'].items():
            if policy['type'] not in policy_types:
                raise DSLParsingLogicException(
                    41,
                    'policy "{0}" of group "{1}" references a non existent '
                    'policy type "{2}"'
                    .format(policy_name, group, policy['type']))
            merged_properties = utils.merge_schema_and_instance_properties(
                policy.get(PROPERTIES, {}),
                policy_types[policy['type']].get(PROPERTIES, {}),
                '{0} \'{1}\' property is not part of '
                'the policy type properties schema',
                '{0} does not provide a value for mandatory '
                '\'{1}\' property which is '
                'part of its policy type schema',
                node_name='group "{0}", policy "{1}"'.format(group_name,
                                                             policy_name))
            policy[PROPERTIES] = merged_properties
            policy['triggers'] = policy.get('triggers', {})
            for trigger_name, trigger in policy['triggers'].items():
                if trigger['type'] not in policy_triggers:
                    raise DSLParsingLogicException(
                        42,
                        'trigger "{0}" of policy "{1}" of group "{2}" '
                        'references a non existent '
                        'policy trigger "{3}"'
                        .format(trigger_name,
                                policy_name,
                                group, trigger['type']))
                merged_parameters = utils.merge_schema_and_instance_properties(
                    trigger.get(PARAMETERS, {}),
                    policy_triggers[trigger['type']].get(PARAMETERS, {}),
                    '{0} \'{1}\' property is not part of '
                    'the policy type properties schema',
                    '{0} does not provide a value for mandatory '
                    '\'{1}\' property which is '
                    'part of its policy type schema',
                    node_name='group "{0}", policy "{1}" trigger "{2}"'
                              .format(group_name, policy_name, trigger_name))
                trigger[PARAMETERS] = merged_parameters
    return processed_groups


def _process_node_relationships(node,
                                node_name,
                                node_names_set,
                                processed_node,
                                top_level_relationships):
    if RELATIONSHIPS in node:
        relationships = []
        for relationship in node[RELATIONSHIPS]:
            relationship_type = relationship['type']
            relationship['type'] = relationship_type
            # validating only the instance relationship values - the inherited
            # relationship values if any
            # should have been validated when the top level relationships were
            # processed.
            # validate target field (done separately since it's only available
            # in instance relationships)
            if relationship['target'] not in node_names_set:
                raise DSLParsingLogicException(
                    25, 'a relationship instance under node {0} of type {1} '
                        'declares an undefined target node {2}'
                        .format(node_name, relationship_type,
                                relationship['target']))
            if relationship['target'] == node_name:
                raise DSLParsingLogicException(
                    23, 'a relationship instance under node {0} of type {1} '
                        'illegally declares the source node as the target node'
                        .format(node_name, relationship_type))
                # merge relationship instance with relationship type
            if relationship_type not in top_level_relationships:
                raise DSLParsingLogicException(
                    26, 'a relationship instance under node {0} declares an '
                        'undefined relationship type {1}'
                        .format(node_name, relationship_type))

            complete_relationship = relationship

            relationship_complete_type = \
                top_level_relationships[relationship_type]

            source_and_target_interfaces = \
                interfaces_parser.\
                merge_relationship_type_and_instance_interfaces(
                    relationship_type=relationship_complete_type,
                    relationship_instance=relationship
                )
            source_interfaces = source_and_target_interfaces[SOURCE_INTERFACES]
            complete_relationship[SOURCE_INTERFACES] = source_interfaces
            target_interfaces = source_and_target_interfaces[TARGET_INTERFACES]
            complete_relationship[TARGET_INTERFACES] = target_interfaces
            complete_relationship[PROPERTIES] = \
                utils.merge_schema_and_instance_properties(
                    relationship.get(PROPERTIES, {}),
                    relationship_complete_type.get(PROPERTIES, {}),
                    '{0} node relationship \'{1}\' property is not part of '
                    'the derived relationship type properties schema',
                    '{0} node relationship does not provide a '
                    'value for mandatory  '
                    '\'{1}\' property which is '
                    'part of its relationship type schema',
                    node_name=node_name
                )
            complete_relationship['target_id'] = \
                complete_relationship['target']
            del (complete_relationship['target'])
            complete_relationship['state'] = 'reachable'
            relationships.append(complete_relationship)

        processed_node[RELATIONSHIPS] = relationships


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


def _process_node(node_name,
                  node,
                  parsed_dsl,
                  top_level_relationships,
                  node_names_set,
                  plugins,
                  resource_base):
    declared_node_type_name = node['type']
    node_type_name = declared_node_type_name
    processed_node = {'name': node_name,
                      'id': node_name,
                      'declared_type': declared_node_type_name}

    # handle types
    if NODE_TYPES not in parsed_dsl or declared_node_type_name not in \
            parsed_dsl[NODE_TYPES]:
        err_message = 'Could not locate node type: {0}; existing types: {1}'\
                      .format(declared_node_type_name,
                              parsed_dsl[NODE_TYPES].keys() if
                              NODE_TYPES in parsed_dsl else 'None')
        raise DSLParsingLogicException(7, err_message)

    processed_node['type'] = node_type_name

    node_type = parsed_dsl[NODE_TYPES][node_type_name]
    complete_node_type = _extract_complete_node(node_type,
                                                node_type_name,
                                                parsed_dsl[NODE_TYPES],
                                                node_name,
                                                node)
    processed_node[PROPERTIES] = complete_node_type[PROPERTIES]
    processed_node[PLUGINS] = {}
    # handle plugins and operations
    if INTERFACES in complete_node_type:
        partial_error_message = 'in node {0} of type {1}'\
            .format(processed_node['id'], processed_node['type'])
        operations = _process_context_operations(
            partial_error_message,
            complete_node_type[INTERFACES],
            plugins,
            processed_node, 10, resource_base)

        processed_node['operations'] = operations

    # handle relationships
    _process_node_relationships(node, node_name, node_names_set,
                                processed_node, top_level_relationships)

    processed_node[PROPERTIES]['cloudify_runtime'] = {}

    processed_node['instances'] = node['instances'] \
        if 'instances' in node else {'deploy': 1}

    return processed_node


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


def _process_plugin(plugin, plugin_name, dsl_version):
    if plugin[constants.PLUGIN_EXECUTOR_KEY] not \
            in [constants.CENTRAL_DEPLOYMENT_AGENT,
                constants.HOST_AGENT]:
        raise DSLParsingLogicException(
            18, 'plugin {0} has an illegal '
                '{1} value {2}; value '
                'must be either {3} or {4}'
            .format(plugin_name,
                    constants.PLUGIN_EXECUTOR_KEY,
                    plugin[constants.PLUGIN_EXECUTOR_KEY],
                    constants.CENTRAL_DEPLOYMENT_AGENT,
                    constants.HOST_AGENT))

    plugin_source = plugin.get(constants.PLUGIN_SOURCE_KEY, None)
    plugin_install = plugin.get(constants.PLUGIN_INSTALL_KEY, True)
    plugin_install_arguments = None

    # if 'install_arguments' are set - verify dsl version is at least 1_1
    if constants.PLUGIN_INSTALL_ARGUMENTS_KEY in plugin:
        if version.is_version_equal_or_greater_than(
                version.parse_dsl_version(dsl_version),
                version.parse_dsl_version(version.DSL_VERSION_1_1)):
            plugin_install_arguments = \
                plugin[constants.PLUGIN_INSTALL_ARGUMENTS_KEY]
        else:
            raise DSLParsingLogicException(
                70,
                'plugin property "{0}" is not supported for {1} earlier than '
                '"{2}". You are currently using version "{3}"'.format(
                    constants.PLUGIN_INSTALL_ARGUMENTS_KEY, version.VERSION,
                    version.DSL_VERSION_1_1, dsl_version))

    if plugin_install and not plugin_source:
        raise DSLParsingLogicException(
            50,
            "plugin {0} needs to be installed, "
            "but does not declare a {1} property"
            .format(plugin_name, constants.PLUGIN_SOURCE_KEY)
        )

    processed_plugin = copy.deepcopy(plugin)

    # augment plugin dictionary
    processed_plugin[constants.PLUGIN_NAME_KEY] = plugin_name
    processed_plugin[constants.PLUGIN_INSTALL_KEY] = plugin_install
    processed_plugin[constants.PLUGIN_SOURCE_KEY] = plugin_source
    processed_plugin[constants.PLUGIN_INSTALL_ARGUMENTS_KEY] = \
        plugin_install_arguments

    return processed_plugin


def _extract_complete_node(node_type,
                           node_type_name,
                           node_types,
                           node_name,
                           node):

    complete_type = extract_complete_node_type(
        node_type=node_type,
        node_types=node_types,
        node_type_name=node_type_name
    )

    complete_node = {
        INTERFACES:
        interfaces_parser.merge_node_type_and_node_template_interfaces(
            node_type=complete_type,
            node_template=node),
        PROPERTIES: utils.merge_schema_and_instance_properties(
            node.get(PROPERTIES, {}),
            complete_type.get(PROPERTIES, {}),
            '{0} node \'{1}\' property is not part of the derived'
            ' type properties schema',
            '{0} node does not provide a '
            'value for mandatory  '
            '\'{1}\' property which is '
            'part of its type schema',
            node_name=node_name
        )
    }

    # merge schema and instance node properties

    return complete_node


def _combine_imports(parsed_dsl, dsl_location, resources_base_url):
    def _merge_into_dict_or_throw_on_duplicate(from_dict, to_dict,
                                               top_level_key, path):
        for _key, _value in from_dict.iteritems():
            if _key not in to_dict:
                to_dict[_key] = _value
            else:
                path.append(_key)
                raise DSLParsingLogicException(
                    4, 'Failed on import: Could not merge {0} due to conflict '
                       'on path {1}'.format(top_level_key, ' --> '.join(path)))

    merge_no_override = set([INTERFACES, NODE_TYPES, PLUGINS, WORKFLOWS,
                             RELATIONSHIPS,
                             POLICY_TYPES, GROUPS, POLICY_TRIGGERS])

    combined_parsed_dsl = copy.deepcopy(parsed_dsl)

    if version.VERSION not in parsed_dsl:
        raise DSLParsingLogicException(
            27, '{0} field must appear in the main blueprint file'.format(
                version.VERSION))

    if IMPORTS not in parsed_dsl:
        return combined_parsed_dsl

    dsl_version = parsed_dsl[version.VERSION]
    _validate_imports_section(parsed_dsl[IMPORTS], dsl_location)

    ordered_imports_list = []
    _build_ordered_imports_list(parsed_dsl, ordered_imports_list,
                                dsl_location,
                                resources_base_url)
    if dsl_location:
        ordered_imports_list = ordered_imports_list[1:]

    for single_import in ordered_imports_list:
        try:
            # (note that this check is only to verify nothing went wrong in
            # the meanwhile, as we've already read
            # from all imported files earlier)
            with contextlib.closing(urllib2.urlopen(single_import)) as f:
                parsed_imported_dsl = _load_yaml(
                    f, 'Failed to parse import {0}'.format(single_import))
        except urllib2.URLError, ex:
            error = DSLParsingLogicException(
                13, 'Failed on import - Unable to open import url {0}; {1}'
                    .format(single_import, ex.message))
            error.failed_import = single_import
            raise error

        if version.VERSION in parsed_imported_dsl:
            imported_dsl_version = parsed_imported_dsl[version.VERSION]
            if imported_dsl_version != dsl_version:
                raise DSLParsingLogicException(
                    28, "An import uses a different "
                        "tosca_definitions_version than the one defined in "
                        "the main blueprint's file: main blueprint's file "
                        "version is {0}, import with different version is {"
                        "1}, version of problematic import is {2}".format(
                            dsl_version, single_import, imported_dsl_version))
            # no need to keep imported dsl's version - it's only used for
            # validation against the main blueprint's version
            del parsed_imported_dsl[version.VERSION]

        # combine the current file with the combined parsed dsl
        # we have thus far
        for key, value in parsed_imported_dsl.iteritems():
            if key == IMPORTS:  # no need to merge those..
                continue
            if key not in combined_parsed_dsl:
                # simply add this first level property to the dsl
                combined_parsed_dsl[key] = value
            else:
                if key in merge_no_override:
                    # this section will combine dictionary entries of the top
                    # level only, with no overrides
                    _merge_into_dict_or_throw_on_duplicate(
                        value, combined_parsed_dsl[key], key, [])
                else:
                    # first level property is not white-listed for merge -
                    # throw an exception
                    raise DSLParsingLogicException(
                        3, 'Failed on import: non-mergeable field: "{0}"'
                           .format(key))

    # clean the now unnecessary 'imports' section from the combined dsl
    if IMPORTS in combined_parsed_dsl:
        del combined_parsed_dsl[IMPORTS]
    return combined_parsed_dsl


def _get_resource_location(resource_name,
                           resources_base_url,
                           current_resource_context=None):
    # Already url format
    if resource_name.startswith('http:')\
            or resource_name.startswith('https:')\
            or resource_name.startswith('file:')\
            or resource_name.startswith('ftp:'):
        return resource_name

    # Points to an existing file
    if os.path.exists(resource_name):
        return 'file:{0}'.format(
            urllib.pathname2url(os.path.abspath(resource_name)))

    if current_resource_context:
        candidate_url = current_resource_context[
            :current_resource_context.rfind('/') + 1] + resource_name
        if _validate_url_exists(candidate_url):
            return candidate_url

    if resources_base_url:
        return resources_base_url + resource_name


def _dsl_location_to_url(dsl_location, resources_base_url):
    if dsl_location is not None:
        dsl_location = _get_resource_location(dsl_location, resources_base_url)
        if dsl_location is None:
            ex = DSLParsingLogicException(30, 'Failed on converting dsl '
                                              'location to url - no suitable '
                                              'location found '
                                              'for dsl {0}'
                                          .format(dsl_location))
            ex.failed_import = dsl_location
            raise ex
    return dsl_location


def _load_yaml(yaml_stream, error_message):
    try:
        # empty string returns None so we convert it to an empty dict
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


def _build_ordered_imports_list(parsed_dsl,
                                ordered_imports_list,
                                current_import,
                                resources_base_url):
    def _build_ordered_imports_list_recursive(_parsed_dsl, _current_import):
        if _current_import is not None:
            ordered_imports_list.append(_current_import)

        if IMPORTS not in _parsed_dsl:
            return

        for another_import in _parsed_dsl[IMPORTS]:
            import_url = _get_resource_location(another_import,
                                                resources_base_url,
                                                _current_import)
            if import_url is None:
                ex = DSLParsingLogicException(
                    13, 'Failed on import - no suitable location found for '
                        'import {0}'.format(another_import))
                ex.failed_import = another_import
                raise ex
            if import_url not in ordered_imports_list:
                try:
                    with contextlib.closing(urllib2.urlopen(import_url)) as f:
                        imported_dsl = _load_yaml(
                            f, 'Failed to parse import {0} (via {1})'
                               .format(another_import, import_url))
                    _build_ordered_imports_list_recursive(imported_dsl,
                                                          import_url)
                except urllib2.URLError, ex:
                    ex = DSLParsingLogicException(
                        13, 'Failed on import - Unable to open import url '
                            '{0}; {1}'.format(import_url, ex.message))
                    ex.failed_import = import_url
                    raise ex

    _build_ordered_imports_list_recursive(parsed_dsl, current_import)


def _validate_dsl_schema(parsed_dsl):
    try:
        jsonschema.validate(parsed_dsl, schemas.DSL_SCHEMA)
    except jsonschema.ValidationError, ex:
        raise DSLParsingFormatException(
            1, '{0}; Path to error: {1}'
               .format(ex.message, '.'.join((str(x) for x in ex.path))))


def _validate_imports_section(imports_section, dsl_location):
    # imports section is validated separately from the main schema since it is
    # validated for each file separately,
    # while the standard validation runs only after combining all imports
    # together
    try:
        jsonschema.validate(imports_section, schemas.IMPORTS_SCHEMA)
    except jsonschema.ValidationError, ex:
        raise DSLParsingFormatException(
            2, 'Improper "imports" section in yaml {0}; {1}; Path to error: '
               '{2}'.format(dsl_location, ex.message,
                            '.'.join((str(x) for x in ex.path))))


def get_plugins_from_operations(node, processed_plugins):
    added_plugins = set()
    plugins = []
    node_operations = node.get('operations', {})
    plugins_from_operations = _get_plugins_from_operations(
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


def _get_plugins_from_operations(operations, processed_plugins):
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
