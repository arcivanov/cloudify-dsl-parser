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

from dsl_parser.elements import (operation,
                                 properties)
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict)


class DerivedFrom(Element):

    schema = Leaf(type=str)


class NodeType(Element):

    schema = {
        'derived_from': DerivedFrom,
        'interfaces': operation.NodeTypeInterfaces,
        'properties': properties.Schema,
    }


class NodeTypes(DictElement):

    schema = Dict(type=NodeType)
