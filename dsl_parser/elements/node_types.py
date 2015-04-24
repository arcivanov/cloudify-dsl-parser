import operation
import properties
from elements import DictElement, Element, Leaf, Dict, List


class DerivedFrom(Element):

    schema = Leaf(type=str)


class NodeType(Element):

    schema = {

        'derived_from': {
            'type': DerivedFrom,
        },

        'interfaces': {
            'type': operation.NodeTypeInterfaces,
        },

        'properties': {
            'type': properties.Schema,
        }

    }


class NodeTypes(DictElement):

    schema = Dict(type=NodeType)
