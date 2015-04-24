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

import copy

from dsl_parser import parser as old_parser
from dsl_parser.elements import (parser,
                                 properties,
                                 operation,
                                 plugins as _plugins)
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict)


class DerivedFrom(Element):

    schema = Leaf(type=str)


class Relationship(Element):

    schema = {
        'derived_from': DerivedFrom,
        'properties': properties.Schema,
        'source_interfaces': operation.NodeTypeInterfaces,
        'target_interfaces': operation.NodeTypeInterfaces,
    }
    requires = {
        'inputs': [parser.Requirement('resource_base', required=False)],
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)]
    }

    def parse(self, plugins, resource_base):
        relationship_type = self.initial_value
        relationship_type_name = self.name
        complete_relationship = old_parser._extract_complete_relationship_type(
            relationship_type=relationship_type,
            relationship_type_name=relationship_type_name,
            relationship_types=self.ancestor(Relationships).initial_value
        )

        old_parser._validate_relationship_fields(
            relationship_type, plugins,
            relationship_type_name,
            resource_base)
        complete_rel_obj_copy = copy.deepcopy(complete_relationship)
        complete_rel_obj_copy['name'] = relationship_type_name
        return complete_rel_obj_copy


class Relationships(DictElement):

    schema = Dict(type=Relationship)
