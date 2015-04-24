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
from dsl_parser.elements import properties
from dsl_parser.elements.elements import (DictElement,
                                          Element,
                                          Leaf,
                                          Dict)


class OperationImplementation(Element):

    schema = Leaf(type=str)


class OperationExecutor(Element):

    schema = Leaf(type=str)

    def validate(self):
        if self.initial_value is None:
            return
        full_operation_name = '{0}.{1}'.format(
            self.ancestor(Interface).name,
            self.ancestor(Operation).name)
        value = self.initial_value
        valid_executors = [constants.CENTRAL_DEPLOYMENT_AGENT,
                           constants.HOST_AGENT]
        if value not in valid_executors:
            raise exceptions.DSLParsingLogicException(
                28, 'Operation {0} has an illegal executor value: {1}. '
                    'valid values are [{2}]'
                    .format(full_operation_name,
                            value,
                            ','.join(valid_executors)))


class NodeTemplateOperationInputs(Element):

    schema = Leaf(type=dict)


class OperationMaxRetries(Element):

    schema = Leaf(type=int)

    def validate(self):
        value = self.initial_value
        if value is not None and value < -1:
            raise ValueError('{0} value must be either -1 to specify unlimited'
                             ' retries or a non negative number but got {1}.'
                             .format(self.name, value))


class OperationRetryInterval(Element):

    schema = Leaf(type=(int, float, long))

    def validate(self):
        value = self.initial_value
        if value is not None and value < 0:
            raise ValueError('{0} value must be a non negative number but got'
                             ' {1}.'.format(self.name, value))


class Operation(Element):
    pass


class NodeTypeOperation(Operation):

    schema = [
        Leaf(type=str),
        {
            'implementation': OperationImplementation,
            'inputs': properties.Schema,
            'executor': OperationExecutor,
            'max_retries': OperationMaxRetries,
            'retry_interval': OperationRetryInterval,
        }
    ]


class NodeTemplateOperation(Operation):

    schema = [
        Leaf(type=str),
        {
            'implementation': OperationImplementation,
            'inputs': NodeTemplateOperationInputs,
            'executor': OperationExecutor,
            'max_retries': OperationMaxRetries,
            'retry_interval': OperationRetryInterval,
        }
    ]


class Interface(DictElement):
    pass


class NodeTemplateInterface(Interface):

    schema = Dict(type=NodeTemplateOperation)


class NodeTemplateInterfaces(Element):

    schema = Dict(type=NodeTemplateInterface)


class NodeTypeInterface(Interface):

    schema = Dict(type=NodeTypeOperation)


class NodeTypeInterfaces(Element):

    schema = Dict(type=NodeTypeInterface)
