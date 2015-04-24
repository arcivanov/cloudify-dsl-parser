from dsl_parser import version

import properties
from elements import DictElement, Element, Leaf, Dict, List


class ToscaDefinitionsVersion(Element):

    required = True
    schema = Leaf(type=str)
    provides = ['version']

    def validate(self):
        version.validate_dsl_version(self.initial_value)

    def parse(self):
        return version.process_dsl_version(self.initial_value)

    def calculate_provided(self):
        return {
            'version': version.parse_dsl_version(self.initial_value)
        }


class OutputDescription(Element):

    schema = Leaf(type=str, version='1_0')


class OutputValue(Element):

    schema = Leaf(type=[list, bool, int, float, long, basestring, dict],
                  version='1_0')


class Output(Element):

    schema = {

        'description': {
            'type': OutputDescription,
            'version': '1_0'
        },

        'value': {
            'type': OutputValue,
            'version': '1_0'
        }

    }


class Outputs(DictElement):

    schema = Dict(type=Output,
                  version='1_0')


class Inputs(properties.Schema):
    pass
