from dsl_parser import exceptions

from elements import DictElement, Element, Leaf, Dict, List


class SchemaPropertyDefault(Element):

    schema = Leaf(type=[list, bool, int, float, long, basestring, dict])


class SchemaPropertyDescription(Element):

    schema = Leaf(type=str)


class SchemaPropertyType(Element):

    schema = Leaf(type=str)

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
        },

        'description': {
            'type': SchemaPropertyDescription,
        },

        'type': {
            'type': SchemaPropertyType,
        }

    }


class Schema(DictElement):

    schema = Dict(type=SchemaProperty)
