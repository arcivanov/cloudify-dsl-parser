from dsl_parser.elements import parser
from dsl_parser import parser as old_parser

from elements import DictElement, Element, Leaf, Dict, List


class Import(Element):

    schema = Leaf(type=str, version='1_0')


class Imports(Element):

    schema = List(type=Import, version='1_0')


class ImportsLoader(Element):

    schema = List(type=Import, version='1_0')
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
            dsl_location = old_parser._dsl_location_to_url(
                blueprint_location,
                resources_base_url)
            self.resource_base = dsl_location[:dsl_location.rfind('/')]
        return old_parser._combine_imports(
            parsed_dsl=main_blueprint,
            dsl_location=blueprint_location,
            resources_base_url=resources_base_url)

    def calculate_provided(self, **kwargs):
        return {
            'resource_base': self.resource_base
        }
