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
        },

        'imports': {
            'type': imports.Imports,
        },

        'inputs': {
            'type': misc.Inputs,
        },

        'plugins': {
            'type': plugins.Plugins,
        },

        'node_types': {
            'type': node_types.NodeTypes,
        },

        'relationships': {
            'type': relationships.Relationships,
        },

        'node_templates': {
            'type': node_templates.NodeTemplates,
        },

        'policy_types': {
            'type': policies.PolicyTypes,
        },

        'policy_triggers': {
            'type': policies.PolicyTriggers,
        },

        'groups': {
            'type': policies.Groups,
        },

        'workflows': {
            'type': workflows.Workflows,
        },

        'outputs': {
            'type': misc.Outputs,
        }

    }

    requires = {
        node_templates.NodeTemplates: ['plan_deployment_plugins'],
        workflows.Workflows: ['workflow_plugins_to_install']
    }

    def parse(self, workflow_plugins_to_install, plan_deployment_plugins):
        plan = models.Plan({
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
            'version': self.child(misc.ToscaDefinitionsVersion).value
        })
        functions.validate_functions(plan)
        return plan
