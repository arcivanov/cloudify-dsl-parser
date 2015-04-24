from dsl_parser import constants
from dsl_parser import exceptions

import properties
from elements import DictElement, Element, Leaf, Dict


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
            'implementation': {
                'type': OperationImplementation,
            },

            'inputs': {
                'type': properties.Schema,
            },

            'executor': {
                'type': OperationExecutor,
            },

            'max_retries': {
                'type': OperationMaxRetries,
            },

            'retry_interval': {
                'type': OperationRetryInterval,
            }
        }
    ]


class NodeTemplateOperation(Operation):

    schema = [
        Leaf(type=str),
        {
            'implementation': {
                'type': OperationImplementation,
            },

            'inputs': {
                'type': NodeTemplateOperationInputs,
            },

            'executor': {
                'type': OperationExecutor,
            },

            'max_retries': {
                'type': OperationMaxRetries,
            },

            'retry_interval': {
                'type': OperationRetryInterval,
            }
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
