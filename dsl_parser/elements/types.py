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

from dsl_parser import exceptions
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf)


class Types(DictElement):
    pass


class Type(Element):
    pass


class DerivedFrom(Element):

    schema = Leaf(type=str)

    descriptor = ''

    def validate(self):
        if self.initial_value is None:
            return

        if self.initial_value not in self.ancestor(Types).initial_value:
            raise exceptions.DSLParsingLogicException(
                14,
                'Missing definition for {0} {1} which is declared as derived '
                'by {0} {2}'
                .format(self.descriptor,
                        self.initial_value,
                        self.ancestor(Type).name))


class RelationshipDerivedFrom(DerivedFrom):

    descriptor = 'type'


class TypeDerivedFrom(DerivedFrom):

    descriptor = 'relationship'