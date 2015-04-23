from dsl_parser import constants
from dsl_parser import exceptions

import properties
from elements import Element, Leaf, Dict


class OperationImplementation(Element):

    schema = Leaf(type=str, version='1_0')


class OperationExecutor(Element):

    schema = Leaf(type=str, version='1_0')

    def validate(self):
        if self.initial_value is None:
            return
        full_operation_name = '{0}.{1}'.format(
            self.ancestor(NodeTemplateInterface).name,
            self.ancestor(NodeTemplateOperation).name)
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

    schema = Leaf(type=dict, version='1_0')


class OperationMaxRetries(Element):

    schema = Leaf(type=int, version='1_0')

    def validate(self):
        value = self.initial_value
        if value is not None and value < -1:
            raise ValueError('{0} value must be either -1 to specify unlimited'
                             ' retries or a non negative number but got {1}.'
                             .format(self.name, value))


class OperationRetryInterval(Element):

    schema = Leaf(type=(int, float, long), version='1_0')

    def validate(self):
        value = self.initial_value
        if value is not None and value < 0:
            raise ValueError('{0} value must be a non negative number but got'
                             ' {1}.'.format(self.name, value))


class NodeTypeOperation(Element):

    schema = [
        Leaf(type=str, version='1_0'),
        {
            'implementation': {
                'type': OperationImplementation,
                'version': '1_0'
            },

            'inputs': {
                'type': properties.Schema,
                'version': '1_0',
            },

            'executor': {
                'type': OperationExecutor,
                'version': '1_0'
            },

            'max_retries': {
                'type': OperationMaxRetries,
                'version': '1_1',
                },

            'retry_interval': {
                'type': OperationRetryInterval,
                'version': '1_1',
                }
        }
    ]


class NodeTemplateOperation(Element):

    schema = [
        Leaf(type=str, version='1_0'),
        {
            'implementation': {
                'type': OperationImplementation,
                'version': '1_0'
            },

            'inputs': {
                'type': NodeTemplateOperationInputs,
                'version': '1_0',
            },

            'executor': {
                'type': OperationExecutor,
                'version': '1_0'
            },

            'max_retries': {
                'type': OperationMaxRetries,
                'version': '1_1',
            },

            'retry_interval': {
                'type': OperationRetryInterval,
                'version': '1_1',
            }
        }
    ]


class NodeTemplateInterface(Element):

    schema = Dict(type=NodeTemplateOperation,
                  version='1_0')


class NodeTemplateInterfaces(Element):

    schema = Dict(type=NodeTemplateInterface,
                  version='1_0')


class NodeTypeInterface(Element):

    schema = Dict(type=NodeTypeOperation,
                  version='1_0')


class NodeTypeInterfaces(Element):

    schema = Dict(type=NodeTypeInterface,
                  version='1_0')
