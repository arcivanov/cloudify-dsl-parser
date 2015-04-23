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


class NodeTemplates(Element):

    schema = Dict(type=NodeTemplate,
                  version='1_0')

    provides = ['node_template_names']

    def calculate_provided(self):
        return {
            'node_template_names': self.build_dict_result().keys()
        }
