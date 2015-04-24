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

import pprint

import yaml

from dsl_parser.elements import (blueprint,
                                 policies,
                                 plugins,
                                 operation,
                                 node_templates,
                                 elements,
                                 parser)


def test_element(element_cls, value, inputs=None):
    p = parser.Parser()
    result = p.parse(value, element_cls=element_cls, inputs=inputs)
    pprint.pprint(result)


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
    test_element(plugins.Plugins, value=plugins_obj)


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
    test_element(operation.NodeTemplateInterfaces,
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
    test_element(PolicyTestElement,
                 value=policies_obj)


def test_version_extractor():
    def test_version(version):
        test_data = 'tosca_definitions_version: cloudify_dsl_{0}'.format(
            version)

        plugins_obj = yaml.load(test_data)
        test_element(blueprint.BlueprintVersionExtractor,
                     value=plugins_obj)
    test_version('1_0')
    test_version('1_1')


def test_blueprint_importer():
    test_data = '''
tosca_definitions_version: cloudify_dsl_1_0
imports:
    - file:///home/dan/dev/cloudify/cloudify-manager/resources/rest-service/cloudify/types/types.yaml  # noqa
    - http://www.getcloudify.org/spec/openstack-plugin/1.2rc1/plugin.yaml

node_types:
    type: {}

'''
    test_obj = yaml.load(test_data)
    inputs = {
        'main_blueprint': test_obj,
        'resources_base_url': None,
        'blueprint_location':
            'file:///home/dan/dev/cloudify/cloudify-manager/blueprint.yaml'
    }
    test_element(blueprint.BlueprintImporter,
                 value=test_obj, inputs=inputs)


def test():
    # test_plugins()
    # test_node_template_interfaces()
    # test_policies()
    # test_version_extractor()
    test_blueprint_importer()

if __name__ == '__main__':
    test()