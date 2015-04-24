from dsl_parser import parser as old_parser

import parser
import node_types as _node_types
import plugins as _plugins
import relationships as _relationships
import operation
from elements import Element, Leaf, Dict, List


class NodeTemplateProperties(Element):

    schema = Leaf(type=dict, version='1_0')


class NodeTemplateRelationshipType(Element):

    schema = Leaf(type=str, version='1_0')


class NodeTemplateRelationshipTarget(Element):

    schema = Leaf(type=str, version='1_0')


class NodeTemplateRelationshipProperties(Element):

    schema = Leaf(type=dict, version='1_0')


class NodeTemplateType(Element):

    schema = Leaf(type=str, version='1_0')


class NodeTemplateInstancesDeploy(Element):

    schema = Leaf(type=int, version='1_0')


class NodeTemplateInstances(Element):

    schema = {

        'deploy': {
            'type': NodeTemplateInstancesDeploy,
            'version': '1_0'
        }

    }


class NodeTemplateRelationship(Element):

    schema = {

        'type': {
            'type': NodeTemplateRelationshipType,
            'version': '1_0',
        },

        'target': {
            'type': NodeTemplateRelationshipTarget,
            'version': '1_0',
        },

        'properties': {
            'type': NodeTemplateRelationshipProperties,
            'version': '1_0'
        },

        'source_interfaces': {
            'type': operation.NodeTemplateInterfaces,
            'version': '1_0'
        },

        'target_interfaces': {
            'type': operation.NodeTemplateInterfaces,
            'version': '1_0'
        }
    }


class NodeTemplateRelationships(Element):

    schema = List(type=NodeTemplateRelationship,
                  version='1_0')


class NodeTemplate(Element):

    schema = {

        'type': {
            'type': NodeTemplateType,
            'version': '1_0'
        },

        'instances': {
            'type': NodeTemplateInstances,
            'version': '1_0'
        },

        'interfaces': {
            'type': operation.NodeTemplateInterfaces,
            'version': '1_0'
        },

        'relationships': {
            'type': NodeTemplateRelationships,
            'version': '1_0'
        },

        'properties': {
            'type': NodeTemplateProperties,
            'version': '1_0'
        }

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
            node=self.initial_value,
            node_types=node_types,
            top_level_relationships=relationships,
            node_names_set=node_names_set,
            plugins=plugins,
            resource_base=resource_base)


class NodeTemplates(Element):

    schema = Dict(type=NodeTemplate,
                  version='1_0')
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
