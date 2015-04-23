from elements import DictElement, Element, Leaf, Dict, List


class SchemaPropertyDefault(Element):

    schema = Leaf(type=[list, bool, int, float, long, basestring, dict],
                  version='1_0')


class SchemaPropertyDescription(Element):

    schema = Leaf(type=str, version='1_0')


class SchemaPropertyType(Element):

    schema = Leaf(type=str, version='1_0')


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
