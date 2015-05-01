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

from dsl_parser import (exceptions,
                        parser as old_parser,
                        utils,
                        constants)
from dsl_parser.elements import (node_types as _node_types,
                                 plugins as _plugins,
                                 relationships as _relationships,
                                 operation)
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
            properties,
            node_type['properties'],
            '{0} node \'{1}\' property is not part of the derived'
            ' type properties schema',
            '{0} node does not provide a '
            'value for mandatory  '
            '\'{1}\' property which is '
            'part of its type schema',
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
            properties,
            relationships[relationship_type_name]['properties'],
            '{0} node relationship \'{1}\' property is not part of '
            'the derived relationship type properties schema',
            '{0} node relationship does not provide a '
            'value for mandatory  '
            '\'{1}\' property which is '
            'part of its relationship type schema',
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
        'source_interfaces': operation.NodeTemplateInterfaces,
        'target_interfaces': operation.NodeTemplateInterfaces,
    }

    requires = {
        _relationships.Relationships: [Value('relationships')],
    }

    def parse(self, relationships):
        result = old_parser._process_node_relationship(
            relationship=self.build_dict_result(),
            relationship_types=relationships)
        result[old_parser.TYPE_HIERARCHY] = _create_type_hierarchy(
            type_name=self.child(NodeTemplateRelationshipType).value,
            types=relationships)
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
        'interfaces': operation.NodeTemplateInterfaces,
        'relationships': NodeTemplateRelationships,
        'properties': NodeTemplateProperties,
    }
    requires = {
        _node_types.NodeTypes: [Value('node_types')]
    }

    def parse(self, node_types):
        node = self.build_dict_result()
        type_hierarchy = _create_type_hierarchy(
            type_name=self.child(NodeTemplateType).value,
            types=node_types)
        node.update({
            'name': self.name,
            'id': self.name,
            'plugins': {},
            old_parser.TYPE_HIERARCHY: type_hierarchy
        })
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
        old_parser._post_process_nodes(
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
