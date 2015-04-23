class ElementType(object):

    def __init__(self, type, version=None):
        if isinstance(type, list):
            type = tuple(type)
        self.type = type
        self.version = version


class Leaf(ElementType):
    pass


class Dict(ElementType):
    pass


class List(ElementType):
    pass


class Element(object):

    required = False
    requires = {}
    provides = []

    def __init__(self, context, initial_value, name=None):
        self.context = context
        self.initial_value = initial_value
        self._parsed_value = None
        self._provided = None
        self.name = name

    def __str__(self):
        return '{0}(name={1}, initial_value={2}, value={3})'.format(
            self.__class__, self.name, self.initial_value,
            self.value)

    __repr__ = __str__

    def validate(self, **kwargs):
        pass

    def parse(self, **kwargs):
        return self.initial_value

    @property
    def value(self):
        return self._parsed_value

    @value.setter
    def value(self, val):
        self._parsed_value = val

    def calculate_provided(self, **kwargs):
        return {}

    @property
    def provided(self):
        return self._provided

    @provided.setter
    def provided(self, value):
        self._provided = value

    def _parent(self):
        return next(self.context.ancestors_iter(self))

    def ancestor(self, element_type):
        matches = [e for e in self.context.ancestors_iter(self)
                   if type(e) == element_type]
        if not matches:
            raise ValueError('No matches found for {0}'.format(element_type))
        if len(matches) > 1:
            raise ValueError('Multiple matches found for {0}'.format(
                element_type))
        return matches[0]

    def child(self, element_type):
        matches = [e for e in self.context.child_elements_iter(self)
                   if type(e) == element_type]
        if not matches:
            raise ValueError('No matches found for {0}'.format(element_type))
        if len(matches) > 1:
            raise ValueError('Multiple matches found for {0}'.format(
                element_type))
        return matches[0]

    def build_dict_result(self):
        return dict((child.name, child.value)
                    for child in self.context.child_elements_iter(self))

    def children(self):
        return list(self.context.child_elements_iter(self))

    def sibling(self, element_type):
        return self._parent().child(element_type)


class DictElement(Element):

    def parse(self, **kwargs):
        return self.build_dict_result()
