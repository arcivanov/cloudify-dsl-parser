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


from dsl_parser import parser as old_parser
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
        return old_parser._extract_complete_node_type(
            node_types=self.ancestor(NodeTypes).initial_value,
            node_type_name=self.name,
            node_type=node_type)


class NodeTypes(types.Types):

    schema = Dict(type=NodeType)
