########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from dsl_parser import (constants,
                        exceptions)
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict)


class PluginExecutor(Element):

    required = True
    schema = Leaf(type=str)

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

    schema = Leaf(type=str)


class PluginInstall(Element):

    schema = Leaf(type=bool)

    def parse(self):
        value = self.initial_value
        return value if value is not None else True


class PluginInstallArguments(Element):

    schema = Leaf(type=str)


class Plugin(DictElement):

    schema = {
        'source': PluginSource,
        'executor': PluginExecutor,
        'install': PluginInstall,
        'install_arguments': PluginInstallArguments,
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

    schema = Dict(type=Plugin)