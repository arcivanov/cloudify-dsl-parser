from dsl_parser import exceptions

from elements import DictElement, Element, Leaf, Dict, List


class SchemaPropertyDefault(Element):

    schema = Leaf(type=[list, bool, int, float, long, basestring, dict],
                  version='1_0')


class SchemaPropertyDescription(Element):

    schema = Leaf(type=str, version='1_0')


class SchemaPropertyType(Element):

    schema = Leaf(type=str, version='1_0')

    def validate(self):
        if self.initial_value is None:
            return
        if self.initial_value not in ['string', 'integer', 'float',
                                      'boolean']:
            raise exceptions.DSLParsingFormatException(
                1,
                'Illegal type: {0}'.format(self.initial_value))


class SchemaProperty(Element):

    schema = {

        'default': {
            'type': SchemaPropertyDefault,
            'version': '1_0'
        },

        'description': {
            'type': SchemaPropertyDescription,
            'version': '1_0'
        },

        'type': {
            'type': SchemaPropertyType,
            'version': '1_0'
        }

    }


class Schema(DictElement):

    schema = Dict(type=SchemaProperty, version='1_0')
