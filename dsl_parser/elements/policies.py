from dsl_parser import exceptions
from dsl_parser import utils

import parser
import node_templates
import properties
from elements import DictElement, Element, Leaf, Dict, List


class PolicyTriggerSource(Element):

    required = True
    schema = Leaf(type=str, version='1_0')


class PolicyTrigger(DictElement):

    schema = {
        'parameters': {
            'type': properties.Schema,
            'version': '1_0'
        },

        'source': {
            'type': PolicyTriggerSource,
            'version': '1_0'
        }
    }


class PolicyTypeSource(Element):

    required = True
    schema = Leaf(type=str, version='1_0')


class PolicyType(DictElement):

    schema = {
        'properties': {
            'type': properties.Schema,
            'version': '1_0'
        },

        'source': {
            'type': PolicyTypeSource,
            'version': '1_0'
        }
    }


class PolicyTypes(DictElement):

    schema = Dict(type=PolicyType)


class PolicyTriggers(DictElement):

    schema = Dict(type=PolicyTrigger)


class GroupPolicyType(Element):

    required = True
    schema = Leaf(type=str, version='1_0')
    requires = {
        PolicyTypes: [parser.Requirement('policy_types', parsed=True)]
    }

    def validate(self, policy_types):
        if self.initial_value not in policy_types:
            raise exceptions.DSLParsingLogicException(
                41,
                'policy "{0}" of group "{1}" references a non existent '
                'policy type "{2}"'
                .format(self.ancestor(GroupPolicy).name,
                        self.ancestor(Group).name,
                        self.initial_value))


class GroupPolicyProperties(Element):

    schema = Leaf(type=dict, version='1_0')
    requires = {
        GroupPolicyType: [],
        PolicyTypes: [parser.Requirement('policy_types', parsed=True)]
    }

    def parse(self, policy_types):
        policy_type = policy_types[self.sibling(GroupPolicyType).value]
        policy_type_properties = policy_type.get('properties', {})
        return utils.merge_schema_and_instance_properties(
            self.initial_value or {},
            policy_type_properties,
            '{0} \'{1}\' property is not part of '
            'the policy type properties schema',
            '{0} does not provide a value for mandatory '
            '\'{1}\' property which is '
            'part of its policy type schema',
            node_name='group "{0}", policy "{1}"'.format(
                self.ancestor(Group).name,
                self.ancestor(GroupPolicy).name))


class GroupPolicyTriggerType(Element):

    required = True
    schema = Leaf(type=str, version='1_0')
    requires = {
        PolicyTriggers: [parser.Requirement('policy_triggers', parsed=True)]
    }

    def validate(self, policy_triggers):
        if self.initial_value not in policy_triggers:
            raise exceptions.DSLParsingLogicException(
                42,
                'trigger "{0}" of policy "{1}" of group "{2}" '
                'references a non existent '
                'policy trigger "{3}"'
                .format(self.ancestor(GroupPolicyTrigger).name,
                        self.ancestor(GroupPolicy).name,
                        self.ancestor(Group).name,
                        self.initial_value))


class GroupPolicyTriggerParameters(Element):

    schema = Leaf(type=dict, version='1_0')
    requires = {
        GroupPolicyTriggerType: [],
        PolicyTriggers: [parser.Requirement('policy_triggers', parsed=True)]
    }

    def parse(self, policy_triggers):
        trigger_type = policy_triggers[
            self.sibling(GroupPolicyTriggerType).value]
        policy_trigger_parameters = trigger_type.get('parameters', {})
        return utils.merge_schema_and_instance_properties(
            self.initial_value or {},
            policy_trigger_parameters,
            '{0} \'{1}\' property is not part of '
            'the policy type properties schema',
            '{0} does not provide a value for mandatory '
            '\'{1}\' property which is '
            'part of its policy type schema',
            node_name='group "{0}", policy "{1}" trigger "{2}"'
                      .format(self.ancestor(Group).name,
                              self.ancestor(GroupPolicy).name,
                              self.ancestor(GroupPolicyTrigger).name))


class GroupPolicyTrigger(DictElement):

    schema = {
        'type': {
            'type': GroupPolicyTriggerType,
            'version': '1_0'
        },

        'parameters': {
            'type': GroupPolicyTriggerParameters,
            'version': '1_0'
        }

    }


class GroupPolicyTriggers(DictElement):

    schema = Dict(type=GroupPolicyTrigger, version='1_0')


class GroupPolicy(DictElement):

    schema = {

        'type': {
            'type': GroupPolicyType,
            'version': '1_0'
        },

        'properties': {
            'type': GroupPolicyProperties,
            'version': '1_0'
        },

        'triggers': {
            'type': GroupPolicyTriggers,
            'version': '1_0'
        }

    }


class GroupMembers(Element):

    required = True
    schema = Leaf(type=list, version='1_0')
    requires = {
        node_templates.NodeTemplates: ['node_template_names']
    }

    def validate(self, node_template_names):
        for member in self.initial_value:
            if member not in node_template_names:
                raise exceptions.DSLParsingLogicException(
                    40,
                    'member "{0}" of group "{1}" does not '
                    'match any defined node'.format(
                        member, self.ancestor(Group).name))

    def parse(self, **kwargs):
        # ensure uniqueness
        return list(set(self.initial_value))


class GroupPolicies(DictElement):

    schema = Dict(type=GroupPolicy, version='1_0')


class Group(DictElement):

    schema = {
        'members': {
            'type': GroupMembers,
            'version': '1_0'
        },

        'policies': {
            'type': GroupPolicies,
            'version': '1_0'
        }
    }


class Groups(DictElement):

    schema = Dict(type=Group)
