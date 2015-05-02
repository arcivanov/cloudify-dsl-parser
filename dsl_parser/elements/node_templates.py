########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import copy

from dsl_parser import (exceptions,
                        parser as old_parser,
                        utils,
                        constants)
from dsl_parser.interfaces import interfaces_parser
from dsl_parser.elements import (node_types as _node_types,
                                 plugins as _plugins,
                                 relationships as _relationships,
                                 operation as _operation)
from dsl_parser.elements.parser import Value, Requirement
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict,
                                          List)


class NodeTemplateType(Element):

    required = True
    schema = Leaf(type=str)
    requires = {
        _node_types.NodeTypes: [Value('node_types')]
    }

    def validate(self, node_types):
        if self.initial_value not in node_types:
            err_message = 'Could not locate node type: {0}; existing types: ' \
                          '{1}' \
                .format(self.initial_value,
                        node_types.keys())
            raise exceptions.DSLParsingLogicException(7, err_message)


class NodeTemplateProperties(Element):

    schema = Leaf(type=dict)
    requires = {
        NodeTemplateType: [],
        _node_types.NodeTypes: [Value('node_types')]
    }

    def parse(self, node_types):
        properties = self.initial_value or {}
        node_type_name = self.sibling(NodeTemplateType).value
        # TODO fix exception tests so this workaround is not required
        if node_type_name not in node_types:
            return properties
        node_type = node_types[node_type_name]
        return utils.merge_schema_and_instance_properties(
            instance_properties=properties,
            schema_properties=node_type['properties'],
            undefined_property_error_message=(
                '{0} node \'{1}\' property is not part of the derived'
                ' type properties schema'),
            missing_property_error_message=(
                '{0} node does not provide a '
                'value for mandatory  '
                '\'{1}\' property which is '
                'part of its type schema'),
            node_name=self.ancestor(NodeTemplate).name)


class NodeTemplateRelationshipType(Element):

    required = True
    schema = Leaf(type=str)
    requires = {
        _relationships.Relationships: [Value('relationships')]
    }

    def validate(self, relationships):
        if self.initial_value not in relationships:
            raise exceptions.DSLParsingLogicException(
                26, 'a relationship instance under node {0} declares an '
                    'undefined relationship type {1}'
                    .format(self.ancestor(NodeTemplate).name,
                            self.initial_value))


class NodeTemplateRelationshipTarget(Element):

    required = True
    schema = Leaf(type=str)

    def validate(self):
        relationship_type = self.sibling(NodeTemplateRelationshipType).name
        node_name = self.ancestor(NodeTemplate).name
        node_template_names = self.ancestor(NodeTemplates).initial_value.keys()
        if self.initial_value not in node_template_names:
            raise exceptions.DSLParsingLogicException(
                25, 'a relationship instance under node {0} of type {1} '
                    'declares an undefined target node {2}'
                    .format(node_name,
                            relationship_type,
                            self.initial_value))
        if self.initial_value == node_name:
            raise exceptions.DSLParsingLogicException(
                23, 'a relationship instance under node {0} of type {1} '
                    'illegally declares the source node as the target node'
                    .format(node_name,
                            relationship_type))


class NodeTemplateRelationshipProperties(Element):

    schema = Leaf(type=dict)
    requires = {
        NodeTemplateRelationshipType: [],
        _relationships.Relationships: [Value('relationships')],
    }

    def parse(self, relationships):
        relationship_type_name = self.sibling(
            NodeTemplateRelationshipType).value
        properties = self.initial_value or {}
        return utils.merge_schema_and_instance_properties(
            instance_properties=properties,
            schema_properties=relationships[relationship_type_name][
                'properties'],
            undefined_property_error_message=(
                '{0} node relationship \'{1}\' property is not part of '
                'the derived relationship type properties schema'),
            missing_property_error_message=(
                '{0} node relationship does not provide a '
                'value for mandatory  '
                '\'{1}\' property which is '
                'part of its relationship type schema'),
            node_name=self.ancestor(NodeTemplate).name)


class NodeTemplateInstancesDeploy(Element):

    required = True
    schema = Leaf(type=int)

    def validate(self):
        if self.initial_value <= 0:
            raise ValueError('deploy instances must be a positive number')


class NodeTemplateInstances(DictElement):

    schema = {
        'deploy': NodeTemplateInstancesDeploy
    }

    def parse(self):
        if self.initial_value is None:
            return {'deploy': 1}
        else:
            return self.initial_value


class NodeTemplateRelationship(Element):

    schema = {
        'type': NodeTemplateRelationshipType,
        'target': NodeTemplateRelationshipTarget,
        'properties': NodeTemplateRelationshipProperties,
        'source_interfaces': _operation.NodeTemplateInterfaces,
        'target_interfaces': _operation.NodeTemplateInterfaces,
    }

    requires = {
        _relationships.Relationships: [Value('relationships')],
    }

    def parse(self, relationships):
        result = self.build_dict_result()
        relationship_type_name = self.child(NodeTemplateRelationshipType).value

        relationship_type = relationships[relationship_type_name]

        for interfaces in [old_parser.SOURCE_INTERFACES,
                           old_parser.TARGET_INTERFACES]:
            result[interfaces] = interfaces_parser. \
                merge_relationship_type_and_instance_interfaces(
                    relationship_type_interfaces=relationship_type[interfaces],
                    relationship_instance_interfaces=result[interfaces])

        result[old_parser.TYPE_HIERARCHY] = _create_type_hierarchy(
            type_name=relationship_type_name,
            types=relationships)

        result['target_id'] = result['target']
        del result['target']

        return result


class NodeTemplateRelationships(Element):

    schema = List(type=NodeTemplateRelationship)

    requires = {
        _relationships.Relationships: [Value('relationships')],
    }

    def validate(self, relationships):
        contained_in_relationships = []
        for relationship in self.children():
            relationship_type = relationship.child(
                NodeTemplateRelationshipType).value
            type_hierarchy = relationship.value[old_parser.TYPE_HIERARCHY]
            if old_parser.CONTAINED_IN_REL_TYPE in type_hierarchy:
                contained_in_relationships.append(relationship_type)

        if len(contained_in_relationships) > 1:
            ex = exceptions.DSLParsingLogicException(
                112, 'Node {0} has more than one relationship that is derived'
                     ' from {1} relationship. Found: {2}'
                     .format(self.ancestor(NodeTemplate).name,
                             old_parser.CONTAINED_IN_REL_TYPE,
                             contained_in_relationships))
            ex.relationship_types = contained_in_relationships
            raise ex

    def parse(self, **kwargs):
        return [c.value for c in sorted(self.children(),
                                        key=lambda child: child.name)]


class NodeTemplate(Element):

    schema = {
        'type': NodeTemplateType,
        'instances': NodeTemplateInstances,
        'interfaces': _operation.NodeTemplateInterfaces,
        'relationships': NodeTemplateRelationships,
        'properties': NodeTemplateProperties,
    }
    requires = {
        'inputs': [Requirement('resource_base', required=False)],
        _plugins.Plugins: [Value('plugins')],
        _node_types.NodeTypes: [Value('node_types')]
    }

    def parse(self, node_types, plugins, resource_base):
        node = self.build_dict_result()
        node.update({
            'name': self.name,
            'id': self.name,
            'plugins': {},
        })

        node_type = node_types[self.child(NodeTemplateType).value]
        interfaces = interfaces_parser.\
            merge_node_type_and_node_template_interfaces(
                node_type_interfaces=node_type[old_parser.INTERFACES],
                node_template_interfaces=node[old_parser.INTERFACES])
        node[old_parser.INTERFACES] = interfaces

        partial_error_message = 'in node {0} of type {1}' \
            .format(node['id'], node['type'])
        operations = _process_operations(
            partial_error_message=partial_error_message,
            interfaces=node[old_parser.INTERFACES],
            plugins=plugins,
            node=node,
            error_code=10,
            resource_base=resource_base)
        node['operations'] = operations

        type_hierarchy = _create_type_hierarchy(
            type_name=self.child(NodeTemplateType).value,
            types=node_types)
        node[old_parser.TYPE_HIERARCHY] = type_hierarchy

        return node


class NodeTemplates(Element):

    required = True
    schema = Dict(type=NodeTemplate)
    requires = {
        'inputs': [Requirement('resource_base', required=False)],
        _relationships.Relationships: [Value('relationships')],
        _plugins.Plugins: [Value('plugins')],
        _node_types.NodeTypes: [Value('node_types')]
    }
    provides = [
        'node_template_names',
        'plan_deployment_plugins'
    ]

    def parse(self, node_types, plugins, relationships, resource_base):
        processed_nodes = [node.value for node in self.children()]
        _post_process_nodes(
            processed_nodes=processed_nodes,
            types=node_types,
            relationships=relationships,
            plugins=plugins,
            resource_base=resource_base)
        return processed_nodes

    def calculate_provided(self, **kwargs):
        return {
            'node_template_names': set(c.name for c in self.children()),
            'plan_deployment_plugins': self._create_plan_deployment_plugins()
        }

    def _create_plan_deployment_plugins(self):
        deployment_plugins = []
        deployment_plugin_names = set()
        for node in self.value:
            if constants.DEPLOYMENT_PLUGINS_TO_INSTALL in node:
                for deployment_plugin in \
                        node[constants.DEPLOYMENT_PLUGINS_TO_INSTALL]:
                    if deployment_plugin[constants.PLUGIN_NAME_KEY] \
                            not in deployment_plugin_names:
                        deployment_plugins.append(deployment_plugin)
                        deployment_plugin_names \
                            .add(deployment_plugin[constants.PLUGIN_NAME_KEY])
        return deployment_plugins


def _post_process_nodes(processed_nodes,
                        types,
                        relationships,
                        plugins,
                        resource_base):
    node_name_to_node = dict((node['id'], node) for node in processed_nodes)
    contained_in_rel_types = _build_family_descendants_set(
        types_dict=relationships,
        derived_from=old_parser.CONTAINED_IN_REL_TYPE)
    for node in processed_nodes:
        _post_process_node_relationships(processed_node=node,
                                         node_name_to_node=node_name_to_node,
                                         plugins=plugins,
                                         resource_base=resource_base)

    # set host_id property to all relevant nodes
    host_types = _build_family_descendants_set(
        types_dict=types,
        derived_from=old_parser.HOST_TYPE)
    for node in processed_nodes:
        host_id = _extract_node_host_id(
            processed_node=node,
            node_name_to_node=node_name_to_node,
            host_types=host_types,
            contained_in_rel_types=contained_in_rel_types)
        if host_id:
            node['host_id'] = host_id

    for node in processed_nodes:
        # fix plugins for all nodes
        node[old_parser.PLUGINS] = _get_plugins_from_operations(
            node=node,
            processed_plugins=plugins)

    # set plugins_to_install property for nodes
    for node in processed_nodes:
        if node['type'] in host_types:
            plugins_to_install = {}
            for another_node in processed_nodes:
                # going over all other nodes, to accumulate plugins
                # from different nodes whose host is the current node
                if another_node.get('host_id') == node['id'] \
                        and old_parser.PLUGINS in another_node:
                    # ok to override here since we assume it is the same plugin
                    for plugin in another_node[old_parser.PLUGINS]:
                        if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                                == constants.HOST_AGENT:
                            plugin_name = plugin['name']
                            plugins_to_install[plugin_name] = plugin
            node['plugins_to_install'] = plugins_to_install.values()

    # set deployment_plugins_to_install property for nodes
    for node in processed_nodes:
        deployment_plugins_to_install = {}
        for plugin in node[old_parser.PLUGINS]:
            if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                    == constants.CENTRAL_DEPLOYMENT_AGENT:
                plugin_name = plugin['name']
                deployment_plugins_to_install[plugin_name] = plugin
        node[constants.DEPLOYMENT_PLUGINS_TO_INSTALL] = \
            deployment_plugins_to_install.values()

    _validate_agent_plugins_on_host_nodes(processed_nodes)


def _post_process_node_relationships(processed_node,
                                     node_name_to_node,
                                     plugins,
                                     resource_base):
    for relationship in processed_node[old_parser.RELATIONSHIPS]:
        target_node = node_name_to_node[relationship['target_id']]
        _process_node_relationships_operations(
            relationship=relationship,
            interfaces_attribute='source_interfaces',
            operations_attribute='source_operations',
            node_for_plugins=processed_node,
            plugins=plugins,
            resource_base=resource_base)
        _process_node_relationships_operations(
            relationship=relationship,
            interfaces_attribute='target_interfaces',
            operations_attribute='target_operations',
            node_for_plugins=target_node,
            plugins=plugins,
            resource_base=resource_base)


def _process_operations(partial_error_message,
                        interfaces,
                        plugins,
                        node,
                        error_code,
                        resource_base):
    operations = {}
    for interface_name, interface in interfaces.items():
        operation_mapping_context = \
            old_parser._extract_plugin_names_and_operation_mapping_from_interface(  # noqa
                interface=interface,
                plugins=plugins,
                error_code=error_code,
                partial_error_message=(
                    'In interface {0} {1}'.format(interface_name,
                                                  partial_error_message)),
                resource_base=resource_base)
        for op_descriptor in operation_mapping_context:
            op_struct = op_descriptor.op_struct
            plugin_name = op_descriptor.op_struct['plugin']
            operation_name = op_descriptor.name
            if op_descriptor.plugin:
                node[old_parser.PLUGINS][plugin_name] = op_descriptor.plugin
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
    partial_error_message = 'in relationship of type {0} in node {1}' \
        .format(relationship['type'],
                node_for_plugins['id'])

    operations = _process_operations(
        partial_error_message=partial_error_message,
        interfaces=relationship[interfaces_attribute],
        plugins=plugins,
        node=node_for_plugins,
        error_code=19,
        resource_base=resource_base)

    relationship[operations_attribute] = operations


def _validate_agent_plugins_on_host_nodes(processed_nodes):
    for node in processed_nodes:
        if 'host_id' not in node:
            for plugin in node[old_parser.PLUGINS]:
                if plugin[constants.PLUGIN_EXECUTOR_KEY] \
                        == constants.HOST_AGENT:
                    raise exceptions.DSLParsingLogicException(
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


def _extract_node_host_id(processed_node,
                          node_name_to_node,
                          host_types,
                          contained_in_rel_types):
    if processed_node['type'] in host_types:
        return processed_node['id']
    else:
        for rel in processed_node[old_parser.RELATIONSHIPS]:
            if rel['type'] in contained_in_rel_types:
                return _extract_node_host_id(
                    node_name_to_node[rel['target_id']],
                    node_name_to_node,
                    host_types,
                    contained_in_rel_types)
    return None


def _get_plugins_from_operations(node, processed_plugins):
    added_plugins = set()
    plugins = []
    node_operations = node['operations']
    plugins_from_operations = _get_plugins_from_operations_helper(
        operations=node_operations,
        processed_plugins=processed_plugins)
    _add_plugins(
        plugins=plugins,
        new_plugins=plugins_from_operations,
        added_plugins=added_plugins)
    plugins_from_node = node['plugins'].values()
    _add_plugins(
        plugins=plugins,
        new_plugins=plugins_from_node,
        added_plugins=added_plugins)
    for relationship in node['relationships']:
        source_operations = relationship['source_operations']
        target_operations = relationship['target_operations']
        _set_operations_executor(
            operations=target_operations,
            processed_plugins=processed_plugins)
        _set_operations_executor(
            operations=source_operations,
            processed_plugins=processed_plugins)
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
            operation=operation,
            processed_plugins=processed_plugins)
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
        _set_operation_executor(operation=operation,
                                processed_plugins=processed_plugins)


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


def _create_type_hierarchy(type_name, types):
    """
    Creates node types hierarchy as list where the last type in the list is
    the actual node type.
    """
    current_type = types[type_name]
    if 'derived_from' in current_type:
        parent_type_name = current_type['derived_from']
        types_hierarchy = _create_type_hierarchy(
            type_name=parent_type_name,
            types=types)
        types_hierarchy.append(type_name)
        return types_hierarchy
    return [type_name]
