from dsl_parser import parser as old_parser
import parser
import plugins as _plugins
import properties
from elements import DictElement, Element, Leaf, Dict


class WorkflowMapping(Element):

    required = True
    schema = Leaf(type=str)


class Workflow(Element):

    required = True
    schema = [
        Leaf(type=str),
        {
            'mapping': {
                'type': WorkflowMapping,
            },

            'parameters': {
                'type': properties.Schema
            }
        }
    ]
    requires = {
        'inputs': [parser.Requirement('resource_base', required=False)],
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)]
    }

    def parse(self, plugins, resource_base):
        op_descriptor = \
            old_parser._extract_plugin_name_and_operation_mapping_from_operation(  # noqa
                plugins=plugins,
                operation_name=self.name,
                operation_content=self.initial_value,
                error_code=21,
                partial_error_message='',
                resource_base=resource_base,
                is_workflows=True)
        return op_descriptor.op_struct


class Workflows(DictElement):

    schema = Dict(type=Workflow)
    requires = {
        _plugins.Plugins: [parser.Requirement('plugins', parsed=True)]
    }
    provides = ['workflow_plugins_to_install']

    def calculate_provided(self, plugins):
        workflow_plugins = []
        workflow_plugin_names = set()
        for workflow, op_struct in self.value.items():
            if op_struct['plugin'] not in workflow_plugin_names:
                plugin_name = op_struct['plugin']
                workflow_plugins.append(plugins[plugin_name])
                workflow_plugin_names.add(plugin_name)
        return {
            'workflow_plugins_to_install': workflow_plugins
        }
