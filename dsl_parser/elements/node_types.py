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
                                 types)
from dsl_parser.elements.elements import Dict


class NodeType(types.Type):

    schema = {
        'derived_from': types.TypeDerivedFrom,
        'interfaces': operation.NodeTypeInterfaces,
        'properties': properties.Schema,
    }

    def parse(self, **kwargs):
        node_type = self.build_dict_result()
        if not node_type.get('derived_from'):
            node_type.pop('derived_from', None)
        return utils.extract_complete_type(
            type_name=self.name,
            type_obj=node_type,
            types=self.ancestor(NodeTypes).initial_value,
            is_relationships=False,
            merging_func=_node_type_merging_function)


class NodeTypes(types.Types):

    schema = Dict(type=NodeType)


def _node_type_merging_function(overridden_node_type,
                                overriding_node_type):

    merged_type = overriding_node_type

    # derive properties
    merged_type[old_parser.PROPERTIES] = utils.merge_sub_dicts(
        overridden_node_type,
        merged_type,
        old_parser.PROPERTIES)

    # derive interfaces
    merged_type[old_parser.INTERFACES] = interfaces_parser.\
        merge_node_type_interfaces(
            overridden_interfaces=overridden_node_type.get(
                old_parser.INTERFACES, {}),
            overriding_interfaces=overriding_node_type.get(
                old_parser.INTERFACES, {}))

    return merged_type
