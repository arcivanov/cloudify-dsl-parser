########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
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


import collections
import copy
import contextlib
import urllib2

import yaml
import yaml.parser

from dsl_parser import (constants,
                        functions)
from dsl_parser.exceptions import (DSLParsingFormatException,
                                   DSLParsingLogicException)
from dsl_parser.framework.parser import Parser


NODE_TEMPLATES = 'node_templates'
IMPORTS = 'imports'
NODE_TYPES = 'node_types'
PLUGINS = 'plugins'
INTERFACES = 'interfaces'
SOURCE_INTERFACES = 'source_interfaces'
TARGET_INTERFACES = 'target_interfaces'
WORKFLOWS = 'workflows'
RELATIONSHIPS = 'relationships'
PROPERTIES = 'properties'
PARAMETERS = 'parameters'
TYPE_HIERARCHY = 'type_hierarchy'
POLICY_TRIGGERS = 'policy_triggers'
POLICY_TYPES = 'policy_types'
GROUPS = 'groups'
INPUTS = 'inputs'
OUTPUTS = 'outputs'

HOST_TYPE = 'cloudify.nodes.Compute'
DEPENDS_ON_REL_TYPE = 'cloudify.relationships.depends_on'
CONTAINED_IN_REL_TYPE = 'cloudify.relationships.contained_in'
CONNECTED_TO_REL_TYPE = 'cloudify.relationships.connected_to'
OpDescriptor = collections.namedtuple('OpDescriptor', [
    'plugin', 'op_struct', 'name'])


def parse_from_path(dsl_file_path, resources_base_url=None):
    with open(dsl_file_path, 'r') as f:
        dsl_string = f.read()
    return _parse(dsl_string, resources_base_url, dsl_file_path)


def parse_from_url(dsl_url, resources_base_url=None):
    try:
        with contextlib.closing(urllib2.urlopen(dsl_url)) as f:
            dsl_string = f.read()
    except urllib2.HTTPError as e:
        if e.code == 404:
            # HTTPError.__str__ uses the 'msg'.
            # by default it is set to 'Not Found' for 404 errors, which is not
            # very helpful, so we override it with a more meaningful message
            # that specifies the missing url.
            e.msg = '{0} not found'.format(e.filename)
        raise
    return _parse(dsl_string, resources_base_url, dsl_url)


def parse(dsl_string, resources_base_url=None):
    return _parse(dsl_string, resources_base_url)


def _parse(dsl_string, resources_base_url, dsl_location=None):
    from dsl_parser.elements import blueprint

    parsed_dsl = _load_yaml(yaml_stream=dsl_string,
                            error_message='Failed to parse DSL')

    parser = Parser()

    # validate and extract version
    parser.parse(parsed_dsl,
                 element_cls=blueprint.BlueprintVersionExtractor,
                 strict=False)

    # handle imports
    result = parser.parse(
        value=parsed_dsl,
        inputs={
            'main_blueprint': parsed_dsl,
            'resources_base_url': resources_base_url,
            'blueprint_location': dsl_location
        },
        element_cls=blueprint.BlueprintImporter,
        strict=False)
    resource_base = result['resource_base']
    merged_blueprint = result['merged_blueprint']

    # parse blueprint
    plan = parser.parse(
        value=merged_blueprint,
        inputs={
            'resource_base': resource_base
        },
        element_cls=blueprint.Blueprint)

    functions.validate_functions(plan)
    return plan


def _extract_plugin_names_and_operation_mapping_from_interface(
        interface,
        plugins,
        error_code,
        partial_error_message,
        resource_base):
    result = []
    for operation_name, operation_content in interface.items():
        op_descriptor = \
            _extract_plugin_name_and_operation_mapping_from_operation(
                plugins=plugins,
                operation_name=operation_name,
                operation_content=operation_content,
                error_code=error_code,
                partial_error_message=partial_error_message,
                resource_base=resource_base)
        result.append(op_descriptor)
    return result


def _extract_plugin_name_and_operation_mapping_from_operation(
        plugins,
        operation_name,
        operation_content,
        error_code,
        partial_error_message,
        resource_base,
        is_workflows=False):
    payload_field_name = 'parameters' if is_workflows else 'inputs'
    mapping_field_name = 'mapping' if is_workflows else 'implementation'
    operation_mapping = operation_content[mapping_field_name]
    operation_payload = operation_content[payload_field_name]

    # only for node operations
    operation_executor = operation_content.get('executor', None)
    operation_max_retries = operation_content.get('max_retries', None)
    operation_retry_interval = operation_content.get('retry_interval', None)

    if not operation_mapping:
        if is_workflows:
            raise RuntimeError('Illegal state. workflow mapping should always'
                               'be defined (enforced by schema validation)')
        else:
            return OpDescriptor(
                name=operation_name,
                plugin='',
                op_struct=_operation_struct(
                    plugin_name='',
                    operation_mapping='',
                    operation_inputs={},
                    executor=None,
                    max_retries=None,
                    retry_interval=None))

    candidate_plugins = [p for p in plugins.keys()
                         if operation_mapping.startswith('{0}.'.format(p))]
    if candidate_plugins:
        if len(candidate_plugins) > 1:
            raise DSLParsingLogicException(
                91, 'Ambiguous operation mapping. [operation={0}, '
                    'plugins={1}]'.format(operation_name, candidate_plugins))
        plugin_name = candidate_plugins[0]
        mapping = operation_mapping[len(plugin_name) + 1:]
        if is_workflows:
            operation_struct = _workflow_operation_struct(
                plugin_name=plugin_name,
                workflow_mapping=mapping,
                workflow_parameters=operation_payload)
        else:
            operation_struct = _operation_struct(
                plugin_name=plugin_name,
                operation_mapping=mapping,
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval)
        return OpDescriptor(
            name=operation_name,
            plugin=plugins[plugin_name],
            op_struct=operation_struct)
    elif resource_base and _resource_exists(resource_base, operation_mapping):
        operation_payload = copy.deepcopy(operation_payload or {})
        if constants.SCRIPT_PATH_PROPERTY in operation_payload:
            message = 'Cannot define {0} property in {1} for {2} "{3}"' \
                .format(constants.SCRIPT_PATH_PROPERTY,
                        operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise DSLParsingLogicException(60, message)
        script_path = operation_mapping
        if is_workflows:
            operation_mapping = constants.SCRIPT_PLUGIN_EXECUTE_WORKFLOW_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: {
                    'default': script_path,
                    'description': 'Workflow script executed by the script'
                                   ' plugin'
                }
            })
        else:
            operation_mapping = constants.SCRIPT_PLUGIN_RUN_TASK
            operation_payload.update({
                constants.SCRIPT_PATH_PROPERTY: script_path
            })
        if constants.SCRIPT_PLUGIN_NAME not in plugins:
            message = 'Script plugin is not defined but it is required for' \
                      ' mapping: {0} of {1} "{2}"' \
                .format(operation_mapping,
                        'workflow' if is_workflows else 'operation',
                        operation_name)
            raise DSLParsingLogicException(61, message)

        if is_workflows:
            operation_struct = _workflow_operation_struct(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                workflow_mapping=operation_mapping,
                workflow_parameters=operation_payload)
        else:
            operation_struct = _operation_struct(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                operation_mapping=operation_mapping,
                operation_inputs=operation_payload,
                executor=operation_executor,
                max_retries=operation_max_retries,
                retry_interval=operation_retry_interval)
        return OpDescriptor(
            name=operation_name,
            plugin=plugins[constants.SCRIPT_PLUGIN_NAME],
            op_struct=operation_struct)
    else:
        # This is an error for validation done somewhere down the
        # current stack trace
        base_error_message = 'Could not extract plugin from {2} ' \
                             'mapping {0}, which is declared for {2} ' \
                             '{1}.'.format(
                                 operation_mapping,
                                 operation_name,
                                 'workflow' if is_workflows else 'operation')
        error_message = base_error_message + partial_error_message
        raise DSLParsingLogicException(error_code, error_message)


def _resource_exists(resource_base, resource_name):
    return _validate_url_exists('{0}/{1}'.format(resource_base, resource_name))


def _operation_struct(plugin_name,
                      operation_mapping,
                      operation_inputs,
                      executor,
                      max_retries,
                      retry_interval):
    return {
        'plugin': plugin_name,
        'operation': operation_mapping,
        'executor': executor,
        'inputs': operation_inputs,
        'has_intrinsic_functions': False,
        'max_retries': max_retries,
        'retry_interval': retry_interval
    }


def _workflow_operation_struct(plugin_name,
                               workflow_mapping,
                               workflow_parameters):
    return {
        'plugin': plugin_name,
        'operation': workflow_mapping,
        'parameters': workflow_parameters
    }


def _load_yaml(yaml_stream, error_message):
    try:
        # load of empty string returns None so we convert it to an empty dict
        return yaml.safe_load(yaml_stream) or {}
    except yaml.parser.ParserError, ex:
        raise DSLParsingFormatException(-1, '{0}: Illegal yaml; {1}'
                                        .format(error_message, ex))


def _validate_url_exists(url):
    try:
        with contextlib.closing(urllib2.urlopen(url)):
            return True
    except urllib2.URLError:
        return False
