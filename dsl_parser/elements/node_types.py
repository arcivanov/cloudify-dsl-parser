import operation
import properties
from elements import Element, Leaf, Dict, List


class DerivedFrom(Element):

    schema = Leaf(type=str, version='1_0')


class NodeType(Element):

    schema = {

        'derived_from': {
            'type': DerivedFrom,
            'version': '1_0'
        },

        'interfaces': {
            'type': operation.NodeTypeInterfaces,
            'version': '1_0'
        },

        'properties': {
            'type': properties.Schema,
            'version': '1_0'
        }

    }


class NodeTypes(Element):

    schema = Dict(type=NodeType,
                  version='1_0')
