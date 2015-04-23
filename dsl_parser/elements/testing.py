import pprint

import yaml

import policies
import plugins
import operation
import node_templates
import elements
from parser import Parser


def test_element(element_cls, element_name, value):
    p = Parser(element_cls=element_cls,
               element_name=element_name)
    context = p.parse(value)
    pprint.pprint(context.element_graph.node)


def test_plugins():
    test_data = '''
p1:
    executor: central_deployment_agent
    source: some_source
    install: true
    install_arguments: --pre
p2:
    executor: host_agent
    install: false
p3:
    executor: host_agent
    source: some_other_source
'''

    plugins_obj = yaml.load(test_data)
    test_element(plugins.Plugins, element_name='plugins', value=plugins_obj)


def test_node_template_interfaces():
    test_data = '''
interface1:
    op1:
        implementation: p1.tasks.op1
        inputs: {}
        executor: host_agent
        max_retries: 10
        retry_interval: 2
    op2:
        implementation: p1.tasks.op2
        inputs: {}
        executor: central_deployment_agent
        max_retries: 10
        retry_interval: 2.0
    op4:
        implementation: p1.tasks.op4
    op3: p1.tasks.op3
'''
    interfaces_obj = yaml.load(test_data)
    test_element(operation.NodeTemplateInterfaces, element_name='interfaces',
                 value=interfaces_obj)


def test_policies():

    class PolicyTestElement(elements.Element):

        schema = {
            'node_templates': {
                'type': node_templates.NodeTemplates
            },
            'policy_types': {
                'type': policies.PolicyTypes
            },
            'policy_triggers': {
                'type': policies.PolicyTriggers
            },
            'groups': {
                'type': policies.Groups
            }
        }

    test_data = '''
node_types:
    type1: {}
node_templates:
    node1:
        type: type1
    node2:
        type: type1
    node3:
        type: type1
policy_types:
    policy_type:
        source: source1
        properties:
            prop1:
                default: 12
                description: this is the description
            prop2: {}

policy_triggers:
    policy_trigger:
        source: source2
        parameters:
            param1:
                default: this_default
            param2: {}

groups:
    group1:
        members: [node1]
        policies:
            policy1:
                type: policy_type
                properties:
                    prop2: value
                triggers:
                    trigger1:
                        type: policy_trigger
                        parameters:
                            param2: another_value
'''
    policies_obj = yaml.load(test_data)
    test_element(PolicyTestElement, element_name='test',
                 value=policies_obj)


def test():
    test_plugins()
    test_node_template_interfaces()
    test_policies()

if __name__ == '__main__':
    test()
