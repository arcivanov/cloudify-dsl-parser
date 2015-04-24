from dsl_parser import parser
from dsl_parser import constants
from dsl_parser import models
from dsl_parser import functions

import imports
import misc
import plugins
import node_types
import node_templates
import relationships
import workflows
import policies
from elements import Element


class BlueprintVersionExtractor(Element):

    schema = {
        'tosca_definitions_version': {
            'type': misc.ToscaDefinitionsVersion,
            'version': '1_0'
        }
    }
    requires = {
        misc.ToscaDefinitionsVersion: ['version']
    }

    def parse(self, version):
        return {
            'version': self.child(misc.ToscaDefinitionsVersion).value,
            'parsed_version': version
        }


class BlueprintImporter(Element):

    schema = {
        'imports': {
            'type': imports.ImportsLoader,
            'version': '1_0',
        },
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

        'tosca_definitions_version': {
            'type': misc.ToscaDefinitionsVersion,
            'version': '1_0'
        },

        'imports': {
            'type': imports.Imports,
            'version': '1_0',
        },

        'inputs': {
            'type': misc.Inputs,
            'version': '1_0',
        },

        'plugins': {
            'type': plugins.Plugins,
            'version': '1_0',
        },

        'node_types': {
            'type': node_types.NodeTypes,
            'version': '1_0',
        },

        'relationships': {
            'type': relationships.Relationships,
            'version': '1_0',
        },

        'node_templates': {
            'type': node_templates.NodeTemplates,
            'version': '1_0',
        },

        'policy_types': {
            'type': policies.PolicyTypes,
            'version': '1_0',
        },

        'policy_triggers': {
            'type': policies.PolicyTriggers,
            'version': '1_0',
        },

        'groups': {
            'type': policies.Groups,
            'version': '1_0'
        },

        'workflows': {
            'type': workflows.Workflows,
            'version': '1_0',
        },

        'outputs': {
            'type': misc.Outputs,
            'version': '1_0',
        }

    }

    requires = {
        workflows.Workflows: ['workflow_plugins_to_install']
    }

    def parse(self, workflow_plugins_to_install):
        plan = models.Plan({
            # constants.NODES: processed_nodes,
            # parser.RELATIONSHIPS: top_level_relationships,
            parser.WORKFLOWS: self.child(workflows.Workflows).value,
            parser.POLICY_TYPES: self.child(policies.PolicyTypes).value,
            parser.POLICY_TRIGGERS: self.child(policies.PolicyTriggers).value,
            parser.GROUPS: self.child(policies.Groups).value,
            parser.INPUTS: self.child(misc.Inputs).value,
            parser.OUTPUTS: self.child(misc.Outputs).value,
            # constants.DEPLOYMENT_PLUGINS_TO_INSTALL: plan_deployment_plugins,
            constants.WORKFLOW_PLUGINS_TO_INSTALL: workflow_plugins_to_install,
            # 'version': version.process_dsl_version(dsl_version)
        })
        functions.validate_functions(plan)
        return plan
