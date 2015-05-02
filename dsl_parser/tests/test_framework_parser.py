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

import testtools

from dsl_parser import exceptions

from dsl_parser.framework import (parser,
                                  elements)


class TestSchemaValidation(testtools.TestCase):

    def setUp(self):
        super(TestSchemaValidation, self).setUp()
        self.parser = parser.Parser()

    def assert_valid(self, value, element_cls, strict=True):
        self.assertEqual(self.parser.parse(value=value,
                                           element_cls=element_cls,
                                           strict=strict),
                         value)

    def assert_invalid(self, value, element_cls, strict=True):
        self.assertRaises(exceptions.DSLParsingFormatException,
                          self.parser.parse,
                          value=value,
                          element_cls=element_cls,
                          strict=strict)

    def test_primitive_leaf_schema_validation(self):
        class TestStrLeaf(elements.Element):
            schema = elements.Leaf(type=str)

        self.assert_valid('some_string', TestStrLeaf)
        self.assert_valid(None, TestStrLeaf)
        self.assert_invalid(12, TestStrLeaf)

    def test_dict_leaf_schema_validation(self):
        class TestDictLeaf(elements.Element):
            schema = elements.Leaf(type=dict)

        self.assert_valid({}, TestDictLeaf)
        self.assert_valid({'key': 'value'}, TestDictLeaf)
        self.assert_valid({'key': None}, TestDictLeaf)
        self.assert_valid({1: '1'}, TestDictLeaf)
        self.assert_valid({None: '1'}, TestDictLeaf)
        self.assert_valid(None, TestDictLeaf)
        self.assert_invalid(12, TestDictLeaf)

    def test_list_leaf_schema_validation(self):
        class TestListLeaf(elements.Element):
            schema = elements.Leaf(type=list)

        self.assert_valid([], TestListLeaf)
        self.assert_valid([1], TestListLeaf)
        self.assert_valid(['one'], TestListLeaf)
        self.assert_valid([None], TestListLeaf)
        self.assert_valid(None, TestListLeaf)
        self.assert_invalid(12, TestListLeaf)

    def test_dict_element_type_schema_validation(self):
        class TestDictValue(elements.Element):
            schema = elements.Leaf(type=str)

        class TestDict(elements.Element):
            schema = elements.Dict(type=TestDictValue)

        self.assert_valid({}, TestDict)
        self.assert_valid({'key': 'value'}, TestDict)
        self.assert_valid({'key': None}, TestDict)
        self.assert_valid(None, TestDict)
        self.assert_invalid(12, TestDict)
        self.assert_invalid({'key': 12}, TestDict)
        self.assert_invalid({12: 'value'}, TestDict)

    def test_schema_dict_schema_validation(self):
        class TestChildElement(elements.Element):
            schema = elements.Leaf(type=str)

        class TestSchemaDict(elements.Element):
            schema = {
                'key': TestChildElement
            }

        self.assert_valid({}, TestSchemaDict)
        self.assert_valid({'key': 'value'}, TestSchemaDict)
        self.assert_valid({'key': None}, TestSchemaDict)
        self.assert_valid(None, TestSchemaDict)
        self.assert_invalid(12, TestSchemaDict)
        self.assert_invalid({'key': 12}, TestSchemaDict)
        self.assert_invalid({'other': 'value'}, TestSchemaDict)
        self.assert_invalid({'other': 12}, TestSchemaDict)
        self.assert_invalid({12: 'value'}, TestSchemaDict, strict=False)
