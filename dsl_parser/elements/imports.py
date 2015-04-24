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

import collections

from dsl_parser import (exceptions,
                        parser as old_parser)
from dsl_parser.elements.elements import (Element,
                                          Leaf,
                                          List)


class Import(Element):

    schema = Leaf(type=str)


class Imports(Element):

    schema = List(type=Import)


class ImportsLoader(Element):

    schema = List(type=Import)
    provides = ['resource_base']
    requires = {
        'inputs': ['main_blueprint',
                   'resources_base_url',
                   'blueprint_location']
    }

    def validate(self, **kwargs):
        imports = [i.value for i in self.children()]
        counter = collections.Counter(imports)
        for count in counter.values():
            if count > 1:
                raise exceptions.DSLParsingFormatException(
                    2, 'Found duplicate imports in {0}'
                       .format(imports))

    def parse(self,
              main_blueprint,
              resources_base_url,
              blueprint_location):
        self.resource_base = None
        if blueprint_location:
            blueprint_location = old_parser._dsl_location_to_url(
                blueprint_location,
                resources_base_url)
            slash_index = blueprint_location.rfind('/')
            self.resource_base = blueprint_location[:slash_index]
        return old_parser._combine_imports(
            parsed_dsl=main_blueprint,
            dsl_location=blueprint_location,
            resources_base_url=resources_base_url)

    def calculate_provided(self, **kwargs):
        return {
            'resource_base': self.resource_base
        }
