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


from dsl_parser import (parser as old_parser,
                        utils)
from dsl_parser.interfaces import interfaces_parser
from dsl_parser.elements import (operation,
                                 properties,
                                 types,
                                 parser)
from dsl_parser.elements.elements import Dict


class NodeType(types.Type):

    schema = {
        'derived_from': types.TypeDerivedFrom,
        'interfaces': operation.NodeTypeInterfaces,
        'properties': properties.Schema,
    }
    requires = {
        'self': [parser.Value('super_type',
                              predicate=types.derived_from_predicate,
                              required=False)]
    }

    def parse(self, super_type):
        node_type = self.build_dict_result()
        if not node_type.get('derived_from'):
            node_type.pop('derived_from', None)
        if super_type:
            node_type[old_parser.PROPERTIES] = utils.merge_sub_dicts(
                overridden_dict=super_type,
                overriding_dict=node_type,
                sub_dict_key=old_parser.PROPERTIES)
            node_type[old_parser.INTERFACES] = interfaces_parser. \
                merge_node_type_interfaces(
                    overridden_interfaces=super_type[old_parser.INTERFACES],
                    overriding_interfaces=node_type[old_parser.INTERFACES])
        node_type[old_parser.TYPE_HIERARCHY] = self.create_type_hierarchy(
            super_type)
        return node_type


class NodeTypes(types.Types):

    schema = Dict(type=NodeType)
    provides = ['host_types']

    def calculate_provided(self):
        return {
            'host_types': _build_family_descendants_set(
                types_dict=self.value,
                derived_from=old_parser.HOST_TYPE)
        }


def _build_family_descendants_set(types_dict, derived_from):
    return set(type_name for type_name in types_dict.iterkeys()
               if _is_derived_from(type_name, types_dict, derived_from))


def _is_derived_from(type_name, _types, derived_from):
    if type_name == derived_from:
        return True
    elif 'derived_from' in _types[type_name]:
        return _is_derived_from(_types[type_name]['derived_from'], _types,
                                derived_from)
    return False
