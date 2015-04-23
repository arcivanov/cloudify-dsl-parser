from dsl_parser import constants
from dsl_parser import exceptions

from elements import DictElement, Element, Leaf, Dict


class PluginExecutor(Element):

    required = True
    schema = Leaf(type=str, version='1_0')

    def validate(self):
        if self.initial_value not in [constants.CENTRAL_DEPLOYMENT_AGENT,
                                      constants.HOST_AGENT]:
            raise exceptions.DSLParsingLogicException(
                18, 'plugin {0} has an illegal '
                    '{1} value {2}; value '
                    'must be either {3} or {4}'
                    .format(self.ancestor(Plugin).name,
                            self.name,
                            self.initial_value,
                            constants.CENTRAL_DEPLOYMENT_AGENT,
                            constants.HOST_AGENT))


class PluginSource(Element):

    schema = Leaf(type=str, version='1_0')


class PluginInstall(Element):

    schema = Leaf(type=bool, version='1_0')

    def parse(self):
        value = self.initial_value
        return value if value is not None else True


class PluginInstallArguments(Element):

    schema = Leaf(type=str, version='1_1')


class Plugin(DictElement):

    schema = {

        'source': {
            'type': PluginSource,
            'version': '1_0'
        },

        'executor': {
            'type': PluginExecutor,
            'version': '1_0'
        },

        'install': {
            'type': PluginInstall,
            'version': '1_0'
        },

        'install_arguments': {
            'type': PluginInstallArguments,
            'version': '1_1'
        },

    }

    def validate(self):
        if (self.child(PluginInstall).value and
                not self.child(PluginSource).value):
            raise exceptions.DSLParsingLogicException(
                50,
                "plugin {0} needs to be installed, "
                "but does not declare a source property"
                .format(self.name))

    def parse(self):
        result = super(Plugin, self).parse()
        result['name'] = self.name
        return result


class Plugins(DictElement):

    schema = Dict(type=Plugin, version='1_0')
