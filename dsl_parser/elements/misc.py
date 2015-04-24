from dsl_parser import version
from dsl_parser import exceptions

import properties
from elements import DictElement, Element, Leaf, Dict, List


class ToscaDefinitionsVersion(Element):

    schema = Leaf(type=str)
    provides = ['version']

    def validate(self):
        if self.initial_value is None:
            raise exceptions.DSLParsingLogicException(
                27, '{0} field must appear in the main blueprint file'.format(
                    version.VERSION))

        version.validate_dsl_version(self.initial_value)

    def parse(self):
        return version.process_dsl_version(self.initial_value)

    def calculate_provided(self):
        return {
            'version': version.parse_dsl_version(self.initial_value)
        }


class OutputDescription(Element):

    schema = Leaf(type=str)


class OutputValue(Element):

    required = True
    schema = Leaf(type=[list, bool, int, float, long, basestring, dict])


class Output(Element):

    schema = {

        'description': {
            'type': OutputDescription,
        },

        'value': {
            'type': OutputValue,
        }

    }


class Outputs(DictElement):

    schema = Dict(type=Output)


class Inputs(properties.Schema):
    pass
