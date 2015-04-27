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

import contextlib
import copy
import os
import urllib
import urllib2

from dsl_parser import (exceptions,
                        parser as old_parser,
                        version)
from dsl_parser.elements.elements import (Element,
                                          Leaf,
                                          List)

MERGE_NO_OVERRIDE = set([
    old_parser.INTERFACES,
    old_parser.NODE_TYPES,
    old_parser.PLUGINS,
    old_parser.WORKFLOWS,
    old_parser.RELATIONSHIPS,
    old_parser.POLICY_TYPES,
    old_parser.GROUPS,
    old_parser.POLICY_TRIGGERS])


class Import(Element):

    schema = Leaf(type=str)


class Imports(Element):

    schema = List(type=Import)


class ImportLoader(Element):

    schema = Leaf(type=str)


class ImportsLoader(Element):

    schema = List(type=ImportLoader)
    provides = ['resource_base']
    requires = {
        'inputs': ['main_blueprint',
                   'resources_base_url',
                   'blueprint_location']
    }

    def __init__(self, *args, **kwargs):
        super(ImportsLoader, self).__init__(*args, **kwargs)
        self.resource_base = None

    def validate(self, **kwargs):
        imports = [i.value for i in self.children()]
        imports_set = set()
        for _import in imports:
            if _import in imports_set:
                raise exceptions.DSLParsingFormatException(
                    2, 'Found duplicate imports in {0}'
                       .format(imports))
            imports_set.add(_import)

    def parse(self,
              main_blueprint,
              resources_base_url,
              blueprint_location):
        if blueprint_location:
            blueprint_location = _dsl_location_to_url(
                dsl_location=blueprint_location,
                resources_base_url=resources_base_url)
            slash_index = blueprint_location.rfind('/')
            self.resource_base = blueprint_location[:slash_index]
        return _combine_imports(parsed_dsl=main_blueprint,
                                dsl_location=blueprint_location,
                                resources_base_url=resources_base_url)

    def calculate_provided(self, **kwargs):
        return {
            'resource_base': self.resource_base
        }


def _dsl_location_to_url(dsl_location, resources_base_url):
    if dsl_location is not None:
        dsl_location = _get_resource_location(dsl_location, resources_base_url)
        if dsl_location is None:
            ex = exceptions.DSLParsingLogicException(
                30, 'Failed on converting dsl '
                    'location to url - no suitable '
                    'location found '
                    'for dsl {0}'
                    .format(dsl_location))
            ex.failed_import = dsl_location
            raise ex
    return dsl_location


def _get_resource_location(resource_name,
                           resources_base_url,
                           current_resource_context=None):
    # Already url format
    url_parts = resource_name.split(':')
    if url_parts[0] in ['http', 'https', 'file', 'ftp']:
        return resource_name

    # Points to an existing file
    if os.path.exists(resource_name):
        return 'file:{0}'.format(
            urllib.pathname2url(os.path.abspath(resource_name)))

    if current_resource_context:
        candidate_url = current_resource_context[
            :current_resource_context.rfind('/') + 1] + resource_name
        if old_parser._validate_url_exists(candidate_url):
            return candidate_url

    if resources_base_url:
        return resources_base_url + resource_name
    else:
        return None


def _combine_imports(parsed_dsl, dsl_location, resources_base_url):
    combined_parsed_dsl = copy.deepcopy(parsed_dsl)

    if old_parser.IMPORTS not in parsed_dsl:
        return combined_parsed_dsl

    ordered_imports = _build_ordered_imports(parsed_dsl,
                                             dsl_location,
                                             resources_base_url)
    if dsl_location:
        ordered_imports = ordered_imports[1:]

    dsl_version = parsed_dsl[version.VERSION]
    for imported in ordered_imports:
        import_url = imported['import']
        parsed_imported_dsl = imported['parsed']
        _validate_and_remove_dsl_version_if_exists(dsl_version,
                                                   import_url,
                                                   parsed_imported_dsl)
        _merge_parsed_into_combined(combined_parsed_dsl,
                                    parsed_imported_dsl)

    # clean the now unnecessary 'imports' section from the combined dsl
    if old_parser.IMPORTS in combined_parsed_dsl:
        del combined_parsed_dsl[old_parser.IMPORTS]
    return combined_parsed_dsl


def _build_ordered_imports(parsed_dsl,
                           dsl_location,
                           resources_base_url):
    ordered_imports = []

    def _build_ordered_imports_recursive(_parsed_dsl, _current_import):
        if _current_import is not None:
            ordered_imports.append({
                'import': _current_import,
                'parsed': _parsed_dsl,
            })

        if old_parser.IMPORTS not in _parsed_dsl:
            return

        imports = [i['import'] for i in ordered_imports]
        for another_import in _parsed_dsl[old_parser.IMPORTS]:
            import_url = _get_resource_location(another_import,
                                                resources_base_url,
                                                _current_import)
            if import_url is None:
                ex = exceptions.DSLParsingLogicException(
                    13, 'Failed on import - no suitable location found for '
                        'import {0}'.format(another_import))
                ex.failed_import = another_import
                raise ex
            if import_url not in imports:
                try:
                    with contextlib.closing(urllib2.urlopen(import_url)) as f:
                        imported_dsl = old_parser._load_yaml(
                            f, 'Failed to parse import {0} (via {1})'
                               .format(another_import, import_url))
                    _build_ordered_imports_recursive(imported_dsl,
                                                     import_url)
                except urllib2.URLError, ex:
                    ex = old_parser.DSLParsingLogicException(
                        13, 'Failed on import - Unable to open import url '
                            '{0}; {1}'.format(import_url, ex.message))
                    ex.failed_import = import_url
                    raise ex

    _build_ordered_imports_recursive(parsed_dsl, dsl_location)
    return ordered_imports


def _validate_and_remove_dsl_version_if_exists(dsl_version,
                                               import_url,
                                               parsed_imported_dsl):
    if version.VERSION in parsed_imported_dsl:
        imported_dsl_version = parsed_imported_dsl[version.VERSION]
        if imported_dsl_version != dsl_version:
            raise exceptions.DSLParsingLogicException(
                28, "An import uses a different "
                    "tosca_definitions_version than the one defined in "
                    "the main blueprint's file: main blueprint's file "
                    "version is {0}, import with different version is {"
                    "1}, version of problematic import is {2}"
                    .format(dsl_version,
                            import_url,
                            imported_dsl_version))
        # no need to keep imported dsl's version - it's only used for
        # validation against the main blueprint's version
        del parsed_imported_dsl[version.VERSION]


def _merge_parsed_into_combined(combined_parsed_dsl, parsed_imported_dsl):
    # combine the current file with the combined parsed dsl
    # we have thus far
    for key, value in parsed_imported_dsl.iteritems():
        if key == old_parser.IMPORTS:  # no need to merge those..
            continue
        if key not in combined_parsed_dsl:
            # simply add this first level property to the dsl
            combined_parsed_dsl[key] = value
        else:
            if key in MERGE_NO_OVERRIDE:
                # this section will combine dictionary entries of the top
                # level only, with no overrides
                _merge_into_dict_or_throw_on_duplicate(
                    value, combined_parsed_dsl[key], key)
            else:
                # first level property is not white-listed for merge -
                # throw an exception
                raise exceptions.DSLParsingLogicException(
                    3, 'Failed on import: non-mergeable field: "{0}"'
                       .format(key))


def _merge_into_dict_or_throw_on_duplicate(from_dict, to_dict,
                                           top_level_key):
    for key, value in from_dict.iteritems():
        if key not in to_dict:
            to_dict[key] = value
        else:
            raise exceptions.DSLParsingLogicException(
                4, 'Failed on import: Could not merge {0} due to conflict '
                   'on {1}'.format(top_level_key, key))
