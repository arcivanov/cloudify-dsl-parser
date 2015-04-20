import collections

from exceptions import DSLParsingLogicException

VERSION = 'tosca_definitions_version'
DSL_VERSION_PREFIX = 'cloudify_dsl_'
DSL_VERSION_1_0 = DSL_VERSION_PREFIX + '1_0'
DSL_VERSION_1_1 = DSL_VERSION_PREFIX + '1_1'
SUPPORTED_VERSIONS = [DSL_VERSION_1_0, DSL_VERSION_1_1]


def validate_dsl_version(dsl_version):
    if dsl_version not in SUPPORTED_VERSIONS:
        raise DSLParsingLogicException(
            29, 'Unexpected tosca_definitions_version {0}; Currently '
                'supported versions are: {1}'.format(dsl_version,
                                                     SUPPORTED_VERSIONS))


def parse_dsl_version(dsl_version):

    if not dsl_version:
        raise DSLParsingLogicException(71, '{0} is missing or empty'
                                       .format(VERSION))

    if not isinstance(dsl_version, basestring):
        raise DSLParsingLogicException(72, 'Invalid {0}: {1} is not a string'
                                       .format(VERSION, dsl_version))

    # handle the 'dsl_version_' prefix
    if dsl_version.startswith(DSL_VERSION_PREFIX):
        short_dsl_version = dsl_version[len(DSL_VERSION_PREFIX):]
    else:
        raise DSLParsingLogicException(73, 'Invalid {0}: "{1}", expected a '
                                           'value following this format: "{2}"'
                                       .format(VERSION, dsl_version,
                                               DSL_VERSION_1_0))

    if not short_dsl_version.__contains__("_"):
        raise DSLParsingLogicException(73, 'Invalid {0}: "{1}", expected a '
                                           'value following this format: "{2}"'
                                       .format(VERSION, dsl_version,
                                               DSL_VERSION_1_0))

    version_parts = short_dsl_version.split('_')
    version_details = collections.namedtuple('version_details',
                                             ['major', 'minor', 'micro'])
    major = version_parts[0]
    minor = version_parts[1]
    micro = None
    if len(version_parts) > 2:
        micro = version_parts[2]

    if not major.isdigit():
        raise DSLParsingLogicException(74,
                                       'Invalid {0}: "{1}", major version '
                                       'is "{2}" while expected to be a number'
                                       .format(VERSION, dsl_version, major))

    if not minor.isdigit():
        raise DSLParsingLogicException(75,
                                       'Invalid {0}: "{1}", minor version '
                                       'is "{2}" while expected to be a number'
                                       .format(VERSION, dsl_version, minor))

    if micro and not micro.isdigit():
        raise DSLParsingLogicException(76,
                                       'Invalid {0}: "{1}", micro version '
                                       'is "{2}" while expected to be a number'
                                       .format(VERSION, dsl_version, micro))

    return version_details(int(major), int(minor),
                           int(micro) if micro else None)


def process_dsl_version(dsl_version):
    version_definitions_name = DSL_VERSION_PREFIX[:-1]
    version_definitions_version = parse_dsl_version(dsl_version)
    if version_definitions_version.micro is None:
        version_definitions_version = (version_definitions_version.major,
                                       version_definitions_version.minor)
    return {
        'raw': dsl_version,
        'definitions_name': version_definitions_name,
        'definitions_version': tuple(version_definitions_version)
    }


def is_version_equal_or_greater_than(version_found, version_required):

    greater_or_equals = False

    if version_found.major > version_required.major:
        greater_or_equals = True
    elif (version_found.major == version_required.major) \
            and (version_found.minor > version_required.minor):
        greater_or_equals = True
    else:
        # comparing micro version, need to treat None as 0
        found_micro_as_int = version_found.micro or 0
        required_micro_as_int = version_required.micro or 0
        if (version_found.major == version_required.major) \
                and (version_found.minor == version_required.minor) \
                and (found_micro_as_int >= required_micro_as_int):
            greater_or_equals = True

    return greater_or_equals
