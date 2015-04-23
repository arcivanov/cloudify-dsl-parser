import misc
import plugins
import node_types
import node_templates
import relationships
import workflows
import policies
import properties
from elements import Element


class Blueprint(Element):

    schema = {

        'tosca_definitions_version': {
            'type': misc.ToscaDefinitionsVersion,
            'version': '1_0'
        },

        'imports': {
            'type': misc.Imports,
            'version': '1_0',
        },

        'inputs': {
            'type': properties.Schema,
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
