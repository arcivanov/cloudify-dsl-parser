import copy

from dsl_parser import parser as old_parser

import plugins as _plugins
import parser
import properties
import operation
from elements import DictElement, Element, Leaf, Dict


class DerivedFrom(Element):

    schema = Leaf(type=str)


class Relationship(Element):

    schema = {

        'derived_from': {
            'type': DerivedFrom,
        },

        'properties': {
            'type': properties.Schema,
        },

        'source_interfaces': {
            'type': operation.NodeTypeInterfaces,
        },

        'target_interfaces': {
            'type': operation.NodeTypeInterfaces,
        }
    }
    requires = {
        'inputs': [parser.Requirement('resource_base', required=False)],
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)]
    }

    def parse(self, plugins, resource_base):
        relationship_type = self.initial_value
        relationship_type_name = self.name
        complete_relationship = old_parser._extract_complete_relationship_type(
            relationship_type=relationship_type,
            relationship_type_name=relationship_type_name,
            relationship_types=self.ancestor(Relationships).initial_value
        )

        old_parser._validate_relationship_fields(
            relationship_type, plugins,
            relationship_type_name,
            resource_base)
        complete_rel_obj_copy = copy.deepcopy(complete_relationship)
        complete_rel_obj_copy['name'] = relationship_type_name
        return complete_rel_obj_copy


class Relationships(DictElement):

    schema = Dict(type=Relationship)
