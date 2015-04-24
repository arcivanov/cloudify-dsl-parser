########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

import testtools
from dsl_parser.constants import INTERFACES
from dsl_parser.interfaces.constants import NO_OP

from dsl_parser.interfaces.interfaces_parser import \
    merge_node_type_interfaces
from dsl_parser.interfaces.interfaces_parser import \
    merge_relationship_type_and_instance_interfaces
from dsl_parser.interfaces.interfaces_parser import \
    merge_node_type_and_node_template_interfaces
from dsl_parser.interfaces.interfaces_parser import \
    merge_relationship_type_interfaces
from dsl_parser.parser import SOURCE_INTERFACES, TARGET_INTERFACES
from dsl_parser.elements import operation

from dsl_parser.tests.interfaces import validate


class InterfacesParserTest(testtools.TestCase):

    def _create_node_type(self, interfaces):
        validate(interfaces, operation.NodeTypeInterfaces)
        return {
            INTERFACES: interfaces
        }

    def _create_node_template(self, interfaces):
        validate(interfaces, operation.NodeTemplateInterfaces)
        return {
            INTERFACES: interfaces
        }

    def _create_relationship_type(self,
                                  source_interfaces=None,
                                  target_interfaces=None):
        result = {}
        if source_interfaces:
            validate(source_interfaces, operation.NodeTypeInterfaces)
            result[SOURCE_INTERFACES] = source_interfaces
        if target_interfaces:
            validate(target_interfaces, operation.NodeTypeInterfaces)
            result[TARGET_INTERFACES] = target_interfaces
        return result

    def _create_relationship_instance(self,
                                      source_interfaces=None,
                                      target_interfaces=None):
        result = {}
        if source_interfaces:
            validate(source_interfaces,
                     operation.NodeTemplateInterfaces)
            result[SOURCE_INTERFACES] = source_interfaces
        if target_interfaces:
            validate(target_interfaces,
                     operation.NodeTemplateInterfaces)
            result[TARGET_INTERFACES] = target_interfaces
        return result

    def test_merge_node_type_interfaces(self):

        overriding_node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        overridden_node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        expected_merged_interfaces = {
            'interface1': {
                'start': {
                    'implementation': 'mock.tasks.start',
                    'inputs': {},
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                },
                'stop': {
                    'implementation': 'mock.tasks.stop',
                    'inputs': {
                        'key': {
                            'default': 'value'
                        }
                    },
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                }
            },
            'interface2': {
                'start': {
                    'implementation': '',
                    'inputs': {},
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                }
            }
        }

        actual_merged_interfaces = merge_node_type_interfaces(
            overriding_node_type=overriding_node_type,
            overridden_node_type=overridden_node_type
        )
        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_node_type_interfaces_no_interfaces_on_overriding(self):

        overriding_node_type = {}
        overridden_node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        expected_merged_interfaces = {
            'interface1': {
                'start': NO_OP,
                'stop': NO_OP
            },
            'interface2': {
                'start': NO_OP
            }
        }

        actual_merged_interfaces = merge_node_type_interfaces(
            overriding_node_type=overriding_node_type,
            overridden_node_type=overridden_node_type
        )
        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_node_type_interfaces_no_interfaces_on_overridden(self):

        overriding_node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )
        overridden_node_type = {}

        expected_merged_interfaces = {
            'interface1': {
                'start': NO_OP,
                'stop': NO_OP
            },
            'interface2': {
                'start': NO_OP
            }
        }

        actual_merged_interfaces = merge_node_type_interfaces(
            overriding_node_type=overriding_node_type,
            overridden_node_type=overridden_node_type
        )
        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_node_type_and_node_template_interfaces(self):

        node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )

        node_template = self._create_node_template(
            interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            'interface1': {
                'start': {
                    'implementation': 'mock.tasks.start-overridden',
                    'inputs': {},
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                },
                'stop': {
                    'implementation': 'mock.tasks.stop',
                    'inputs': {
                        'key': 'value'
                    },
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                }
            }
        }

        actual_merged_interfaces = \
            merge_node_type_and_node_template_interfaces(
                node_type=node_type,
                node_template=node_template
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_node_type_no_interfaces_and_node_template_interfaces(self):

        node_type = {}
        node_template = self._create_node_template(
            interfaces={
                'interface1': {
                    'start': 'mock.tasks.start'
                }
            }
        )

        expected_merged_interfaces = {
            'interface1': {
                'start': {
                    'implementation': 'mock.tasks.start',
                    'inputs': {},
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                }
            }
        }

        actual_merged_interfaces = \
            merge_node_type_and_node_template_interfaces(
                node_type=node_type,
                node_template=node_template
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_node_type_interfaces_and_node_template_no_interfaces(self):

        node_type = self._create_node_type(
            interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    }
                }
            }
        )
        node_template = {}

        expected_merged_interfaces = {
            'interface1': {
                'start': {
                    'implementation': 'mock.tasks.start',
                    'inputs': {},
                    'executor': None,
                    'max_retries': None,
                    'retry_interval': None
                }
            }
        }

        actual_merged_interfaces = \
            merge_node_type_and_node_template_interfaces(
                node_type=node_type,
                node_template=node_template
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_interfaces(self):

        overriding_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        overridden_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                },
                'interface2': {
                    'start': {
                        'implementation': '',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                },
                'interface2': {
                    'start': {
                        'implementation': '',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }
        actual_merged_interfaces = merge_relationship_type_interfaces(
            overriding_relationship_type=overriding_relationship_type,
            overridden_relationship_type=overridden_relationship_type
        )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_interfaces_no_source_interfaces_on_overriding(self):  # NOQA

        overriding_relationship_type = self._create_relationship_type(
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        overridden_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                },
                'interface2': {
                    'start': {
                        'implementation': '',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }
        actual_merged_interfaces = merge_relationship_type_interfaces(
            overriding_relationship_type=overriding_relationship_type,
            overridden_relationship_type=overridden_relationship_type
        )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_interfaces_no_source_interfaces_on_overridden(self):  # NOQA

        overriding_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        overridden_relationship_type = self._create_relationship_type(
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            }
        }
        actual_merged_interfaces = merge_relationship_type_interfaces(
            overriding_relationship_type=overriding_relationship_type,
            overridden_relationship_type=overridden_relationship_type
        )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_interfaces_no_target_interfaces_on_overriding(self):  # NOQA

        overriding_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        overridden_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                },
                'interface2': {
                    'start': NO_OP
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            }
        }
        actual_merged_interfaces = merge_relationship_type_interfaces(
            overriding_relationship_type=overriding_relationship_type,
            overridden_relationship_type=overridden_relationship_type
        )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_interfaces_no_target_interfaces_on_overridden(self):  # NOQA

        overriding_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {},
                    'stop': {}
                },
                'interface2': {
                    'start': {}
                }
            }
        )

        overridden_relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': NO_OP,
                    'stop': NO_OP
                },
                'interface2': {
                    'start': NO_OP
                }
            }
        }
        actual_merged_interfaces = merge_relationship_type_interfaces(
            overriding_relationship_type=overriding_relationship_type,
            overridden_relationship_type=overridden_relationship_type
        )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_and_instance_interfaces(self):

        relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        relationship_instance = self._create_relationship_instance(
            source_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            },
            target_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }

        actual_merged_interfaces = \
            merge_relationship_type_and_instance_interfaces(
                relationship_type=relationship_type,
                relationship_instance=relationship_instance
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_no_source_interfaces_and_instance_interfaces(self):  # NOQA

        relationship_type = self._create_relationship_type(
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        relationship_instance = self._create_relationship_instance(
            source_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            },
            target_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }

        actual_merged_interfaces = \
            merge_relationship_type_and_instance_interfaces(
                relationship_type=relationship_type,
                relationship_instance=relationship_instance
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_no_target_interfaces_type_and_instance_interfaces(self):  # NOQA

        relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        relationship_instance = self._create_relationship_instance(
            source_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            },
            target_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }

        actual_merged_interfaces = \
            merge_relationship_type_and_instance_interfaces(
                relationship_type=relationship_type,
                relationship_instance=relationship_instance
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_and_instance_no_source_interfaces(self):

        relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        relationship_instance = self._create_relationship_instance(
            target_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }

        actual_merged_interfaces = \
            merge_relationship_type_and_instance_interfaces(
                relationship_type=relationship_type,
                relationship_instance=relationship_instance
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)

    def test_merge_relationship_type_and_instance_no_target_interfaces(self):

        relationship_type = self._create_relationship_type(
            source_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            },
            target_interfaces={
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start'
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': {
                                'default': 'value'
                            }
                        }
                    }
                }
            }
        )
        relationship_instance = self._create_relationship_instance(
            source_interfaces={
                'interface1': {
                    'start': 'mock.tasks.start-overridden'
                }
            }
        )

        expected_merged_interfaces = {
            SOURCE_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start-overridden',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            },
            TARGET_INTERFACES: {
                'interface1': {
                    'start': {
                        'implementation': 'mock.tasks.start',
                        'inputs': {},
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    },
                    'stop': {
                        'implementation': 'mock.tasks.stop',
                        'inputs': {
                            'key': 'value'
                        },
                        'executor': None,
                        'max_retries': None,
                        'retry_interval': None
                    }
                }
            }
        }

        actual_merged_interfaces = \
            merge_relationship_type_and_instance_interfaces(
                relationship_type=relationship_type,
                relationship_instance=relationship_instance
            )

        self.assertEqual(actual_merged_interfaces,
                         expected_merged_interfaces)
