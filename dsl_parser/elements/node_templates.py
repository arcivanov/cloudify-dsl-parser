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
                        parser as old_parser)
from dsl_parser.elements import (parser,
                                 node_types as _node_types,
                                 plugins as _plugins,
                                 relationships as _relationships,
                                 operation)
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict,
                                          List)


class NodeTemplateProperties(Element):

    schema = Leaf(type=dict)

    def parse(self):
        return self.initial_value or {}


class NodeTemplateRelationshipType(Element):

    required = True
    schema = Leaf(type=str)


class NodeTemplateRelationshipTarget(Element):

    required = True
    schema = Leaf(type=str)


class NodeTemplateRelationshipProperties(Element):

    schema = Leaf(type=dict)

    def parse(self):
        return self.initial_value or {}


class NodeTemplateType(Element):

    required = True
    schema = Leaf(type=str)
    requires = {
        _node_types.NodeTypes: [parser.Requirement('node_types', parsed=True)]
    }

    def validate(self, node_types):
        if self.initial_value not in node_types:
            err_message = 'Could not locate node type: {0}; existing types: ' \
                          '{1}' \
                .format(self.initial_value,
                        node_types.keys())
            raise exceptions.DSLParsingLogicException(7, err_message)


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


class NodeTemplateRelationship(DictElement):

    schema = {
        'type': NodeTemplateRelationshipType,
        'target': NodeTemplateRelationshipTarget,
        'properties': NodeTemplateRelationshipProperties,
        'source_interfaces': operation.NodeTemplateInterfaces,
        'target_interfaces': operation.NodeTemplateInterfaces,
    }


class NodeTemplateRelationships(Element):

    schema = List(type=NodeTemplateRelationship)

    def parse(self):
        return self.initial_value or []


class NodeTemplate(Element):

    schema = {
        'type': NodeTemplateType,
        'instances': NodeTemplateInstances,
        'interfaces': operation.NodeTemplateInterfaces,
        'relationships': NodeTemplateRelationships,
        'properties': NodeTemplateProperties,
    }
    requires = {
        'inputs': [parser.Requirement('resource_base', required=False)],
        _relationships.Relationships: [parser.Requirement('relationships',
                                                          parsed=True)],
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)],
        _node_types.NodeTypes: [parser.Requirement('node_types',
                                                   parsed=True)]
    }

    def parse(self, node_types, relationships, plugins, resource_base):
        node_names_set = set(self.ancestor(NodeTemplates).initial_value.keys())
        return old_parser._process_node(
            node_name=self.name,
            node=self.build_dict_result(),
            node_types=node_types,
            top_level_relationships=relationships,
            node_names_set=node_names_set,
            plugins=plugins,
            resource_base=resource_base)


class NodeTemplates(Element):

    required = True
    schema = Dict(type=NodeTemplate)
    requires = {
        'inputs': [parser.Requirement('resource_base', required=False)],
        _relationships.Relationships: [parser.Requirement('relationships',
                                                          parsed=True)],
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)],
        _node_types.NodeTypes: [parser.Requirement('node_types',
                                                   parsed=True)]
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
        plan_deployment_plugins = old_parser._create_plan_deployment_plugins(
            processed_nodes=self.value)
        return {
            'node_template_names': set(c.name for c in self.children()),
            'plan_deployment_plugins': plan_deployment_plugins
        }
