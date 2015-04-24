from dsl_parser.elements import parser
from dsl_parser import parser as old_parser

from elements import DictElement, Element, Leaf, Dict, List


class Import(Element):

    schema = Leaf(type=str)


class Imports(Element):

    schema = List(type=Import)


class ImportsLoader(Element):

    schema = List(type=Import)
    provides = ['resource_base']
    requires = {
        'inputs': ['main_blueprint',
                   'resources_base_url',
                   'blueprint_location']
    }

    def parse(self,
              main_blueprint,
              resources_base_url,
              blueprint_location):
        self.resource_base = None
        if blueprint_location:
            blueprint_location = old_parser._dsl_location_to_url(
                blueprint_location,
                resources_base_url)
            slash_index = blueprint_location.rfind('/')
            self.resource_base = blueprint_location[:slash_index]
        return old_parser._combine_imports(
            parsed_dsl=main_blueprint,
            dsl_location=blueprint_location,
            resources_base_url=resources_base_url)

    def calculate_provided(self, **kwargs):
        return {
            'resource_base': self.resource_base
        }
