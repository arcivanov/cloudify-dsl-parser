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
from dsl_parser.framework.requirements import Value, Requirement
from dsl_parser.framework.elements import (DictElement,
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


def _node_template_relationship_type_predicate(source, target):
    try:
        return (source.child(NodeTemplateRelationshipType).initial_value ==
                target.name)
    except exceptions.DSLParsingElementMatchException:
        return False


class NodeTemplateRelationship(Element):

    schema = {
        'type': NodeTemplateRelationshipType,
        'target': NodeTemplateRelationshipTarget,
        'properties': NodeTemplateRelationshipProperties,
        'source_interfaces': _operation.NodeTemplateInterfaces,
        'target_interfaces': _operation.NodeTemplateInterfaces,
    }

    requires = {
        _relationships.Relationship: [
            Value('relationship_type',
                  predicate=_node_template_relationship_type_predicate)]
    }

    def parse(self, relationship_type):
        result = self.build_dict_result()
        for interfaces in [old_parser.SOURCE_INTERFACES,
                           old_parser.TARGET_INTERFACES]:
            result[interfaces] = interfaces_parser. \
                merge_relationship_type_and_instance_interfaces(
                    relationship_type_interfaces=relationship_type[interfaces],
                    relationship_instance_interfaces=result[interfaces])

        result[old_parser.TYPE_HIERARCHY] = relationship_type[
            old_parser.TYPE_HIERARCHY]

        result['target_id'] = result['target']
        del result['target']

        return result


class NodeTemplateRelationships(Element):

    schema = List(type=NodeTemplateRelationship)

    requires = {
        _relationships.Relationships: [Value('relationships')],
    }
    provides = ['contained_in']

    def validate(self, relationships):
        contained_in_relationships = []
        contained_in_targets = []
        for relationship in self.children():
            relationship_target = relationship.child(
                NodeTemplateRelationshipTarget).value
            relationship_type = relationship.child(
                NodeTemplateRelationshipType).value
            type_hierarchy = relationship.value[old_parser.TYPE_HIERARCHY]
            if old_parser.CONTAINED_IN_REL_TYPE in type_hierarchy:
                contained_in_relationships.append(relationship_type)
                contained_in_targets.append(relationship_target)

        if len(contained_in_relationships) > 1:
            ex = exceptions.DSLParsingLogicException(
                112, 'Node {0} has more than one relationship that is derived'
                     ' from {1} relationship. Found: {2} for targets: {3}'
                     .format(self.ancestor(NodeTemplate).name,
                             old_parser.CONTAINED_IN_REL_TYPE,
                             contained_in_relationships,
                             contained_in_targets))
            ex.relationship_types = contained_in_relationships
            raise ex

    def parse(self, **kwargs):
        return [c.value for c in sorted(self.children(),
                                        key=lambda child: child.name)]

    def calculate_provided(self, **kwargs):
        contained_in_list = [r.child(NodeTemplateRelationshipTarget).value
                             for r in self.children()
                             if old_parser.CONTAINED_IN_REL_TYPE in
                             r.value[old_parser.TYPE_HIERARCHY]]
        contained_in = contained_in_list[0] if contained_in_list else None
        return {
            'contained_in': contained_in
        }


def _node_template_related_nodes_predicate(source, target):
    if source.name == target.name:
        return False
    targets = source.descendants(NodeTemplateRelationshipTarget)
    relationship_targets = [e.initial_value for e in targets]
    return target.name in relationship_targets


def _node_template_node_type_predicate(source, target):
    try:
        return (source.child(NodeTemplateType).initial_value ==
                target.name)
    except exceptions.DSLParsingElementMatchException:
        return False


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
        'self': [Value('related_node_templates',
                       predicate=_node_template_related_nodes_predicate,
                       multiple_results=True)],
        _plugins.Plugins: [Value('plugins')],
        _node_types.NodeType: [
            Value('node_type',
                  predicate=_node_template_node_type_predicate)],
        _node_types.NodeTypes: ['host_types']
    }

    def parse(self,
              node_type,
              host_types,
              plugins,
              resource_base,
              related_node_templates):
        node = self.build_dict_result()
        node.update({
            'name': self.name,
            'id': self.name,
            'plugins': {},
            old_parser.TYPE_HIERARCHY: node_type[old_parser.TYPE_HIERARCHY]
        })

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
            node_plugins=node[old_parser.PLUGINS],
            error_code=10,
            resource_base=resource_base)
        node['operations'] = operations

        node_name_to_node = dict((node['id'], node)
                                 for node in related_node_templates)
        _post_process_node_relationships(processed_node=node,
                                         node_name_to_node=node_name_to_node,
                                         plugins=plugins,
                                         resource_base=resource_base)

        contained_in = self.child(NodeTemplateRelationships).provided[
            'contained_in']
        if contained_in:
            containing_node = [n for n in related_node_templates
                               if n['name'] == contained_in][0]
            if 'host_id' in containing_node:
                node['host_id'] = containing_node['host_id']
        else:
            if self.child(NodeTemplateType).value in host_types:
                node['host_id'] = self.name

        return node


class NodeTemplates(Element):

    required = True
    schema = Dict(type=NodeTemplate)
    requires = {
        _plugins.Plugins: [Value('plugins')],
        _node_types.NodeTypes: ['host_types']
    }
    provides = [
        'node_template_names',
        'plan_deployment_plugins'
    ]

    def parse(self, host_types, plugins):
        processed_nodes = [node.value for node in self.children()]
        _post_process_nodes(
            processed_nodes=processed_nodes,
            host_types=host_types,
            plugins=plugins)
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
                        host_types,
                        plugins):
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
                        node_plugins,
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
                node_plugins[plugin_name] = op_descriptor.plugin
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
        node_plugins=node_for_plugins[old_parser.PLUGINS],
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
