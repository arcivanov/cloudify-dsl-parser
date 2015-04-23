import properties
import operation
from elements import Element, Leaf, Dict, List


class DerivedFrom(Element):

    schema = Leaf(type=str, version='1_0')


class Relationship(Element):

    schema = {

        'derived_from': {
            'type': DerivedFrom,
            'version': '1_0'
        },

        'properties': {
            'type': properties.Schema,
            'version': '1_0'
        },

        'source_interfaces': {
            'type': operation.NodeTypeInterfaces,
            'version': '1_0'
        },

        'target_interfaces': {
            'type': operation.NodeTypeInterfaces,
            'version': '1_0'
        }
    }


class Relationships(Element):

    schema = Dict(type=Relationship, version='1_0')
