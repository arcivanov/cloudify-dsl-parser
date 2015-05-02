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

from dsl_parser import (parser,
                        constants,
                        models)
from dsl_parser.elements import (imports,
                                 misc,
                                 plugins,
                                 node_types,
                                 node_templates,
                                 relationships,
                                 workflows,
                                 policies)
from dsl_parser.framework.elements import Element


class BlueprintVersionExtractor(Element):

    schema = {
        'tosca_definitions_version': misc.ToscaDefinitionsVersion
    }
    requires = {
        misc.ToscaDefinitionsVersion: ['version']
    }

    def parse(self, version):
        return version


class BlueprintImporter(Element):

    schema = {
        'imports': imports.ImportsLoader,
    }
    requires = {
        imports.ImportsLoader: ['resource_base']
    }

    def parse(self, resource_base):
        return {
            'merged_blueprint': self.child(imports.ImportsLoader).value,
            'resource_base': resource_base
        }


class Blueprint(Element):

    schema = {
        'tosca_definitions_version': misc.ToscaDefinitionsVersion,
        'imports': imports.Imports,
        'inputs': misc.Inputs,
        'plugins': plugins.Plugins,
        'node_types': node_types.NodeTypes,
        'relationships': relationships.Relationships,
        'node_templates': node_templates.NodeTemplates,
        'policy_types': policies.PolicyTypes,
        'policy_triggers': policies.PolicyTriggers,
        'groups': policies.Groups,
        'workflows': workflows.Workflows,
        'outputs': misc.Outputs,
    }
    requires = {
        node_templates.NodeTemplates: ['plan_deployment_plugins'],
        workflows.Workflows: ['workflow_plugins_to_install']
    }

    def parse(self, workflow_plugins_to_install, plan_deployment_plugins):
        return models.Plan({
            constants.NODES: self.child(node_templates.NodeTemplates).value,
            parser.RELATIONSHIPS: self.child(
                relationships.Relationships).value,
            parser.WORKFLOWS: self.child(workflows.Workflows).value,
            parser.POLICY_TYPES: self.child(policies.PolicyTypes).value,
            parser.POLICY_TRIGGERS: self.child(policies.PolicyTriggers).value,
            parser.GROUPS: self.child(policies.Groups).value,
            parser.INPUTS: self.child(misc.Inputs).value,
            parser.OUTPUTS: self.child(misc.Outputs).value,
            constants.DEPLOYMENT_PLUGINS_TO_INSTALL: plan_deployment_plugins,
            constants.WORKFLOW_PLUGINS_TO_INSTALL: workflow_plugins_to_install,
            constants.VERSION: self.child(misc.ToscaDefinitionsVersion).value
        })
