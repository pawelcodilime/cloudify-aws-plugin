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

# Built-in Imports
import testtools

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import constants
from ec2 import connection
from ec2 import securitygroup
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError


class TestSecurityGroup(testtools.TestCase):

    def security_group_mock(self, test_name, test_properties):
        """ Creates a mock context for security group tests
            with given properties
        """

        ctx = MockCloudifyContext(
            node_id=test_name,
            properties=test_properties
        )

        return ctx

    def get_mock_properties(self):

        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '22',
                    'to_port': '22',
                    'cidr_ip': '127.0.0.1/32'
                },
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        return test_properties

    @mock_ec2
    def test_create(self):
        """This tests that create runs"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_create', test_properties)
        current_ctx.set(ctx=ctx)
        securitygroup.create(ctx=ctx)

    @mock_ec2
    def test_create_existing(self):
        """This tests that create creates the runtime_properties"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_duplicate', test_properties)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(name, description)
        ctx.node.properties['use_external_resource'] = True
        securitygroup.create(ctx=ctx)
        self.assertEqual(
            ctx.instance.runtime_properties['aws_resource_id'],
            group.id)

    @mock_ec2
    def test_delete(self):
        """This tests that delete removes the runtime_properties"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_delete', test_properties)
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        securitygroup.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_duplicate(self):
        """This tests that when you give a name of an existing
        resource, a NonRecoverableError is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_duplicate', test_properties)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        ec2_client.create_security_group(name, description)
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn('InvalidGroup.Duplicate', ex.message)

    @mock_ec2
    def test_delete_deleted(self):
        """This tests that security group delete raises an
        error when the group is already deleted.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_delete_deleted', test_properties)
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_delete_deleted',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        ec2_client.delete_security_group(group_id=group.id)
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.delete, ctx=ctx)
        self.assertIn('does not exist in the account', ex.message)

    @mock_ec2
    def test_delete_existing(self):
        """This tests that security group delete removed the
        runtime_properties
        """
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_delete_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_delete_existing',
                                                 'this is test')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        securitygroup.delete(ctx=ctx)
        self.assertNotIn(
            'aws_resource_id',
            ctx.instance.runtime_properties)

    @mock_ec2
    def test_use_external_not_existing(self):
        """This tests that when use_external_resource is true
        if such a security group not exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_use_external_not_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn(
            'but the given security group does not exist', ex.message)

    @mock_ec2
    def test_creation_validation_existing(self):
        """This tests that when use_external_resource is true
        if such a security group not exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_creation_validation_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.creation_validation, ctx=ctx)
        self.assertIn(
            'External resource, but the supplied security group', ex.message)

    @mock_ec2
    def test_creation_validation_not_existing(self):
        """This tests that when use_external_resource is false
        if such a security group exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_creation_validation_not_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(
            'test_creation_validation_not_existing',
            'this is a test')
        ctx.node.properties['resource_id'] = group.id
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.creation_validation, ctx=ctx)
        self.assertIn(
            'Not external resource, but the supplied security group',
            ex.message)

    @mock_ec2
    def test_create_group_rules(self):
        """ This tests that _create_group_rules creates
        the rules and that they match on the way out
        to what when in.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_group_rules', test_properties)
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_create_group_rules',
                                                 'this is test')
        securitygroup._create_group_rules(group)
        self.assertEqual(
            str(group.rules),
            str(ec2_client.get_all_security_groups(
                groupnames='test_create_group_rules')[0].rules))

    def test_get_security_group_from_name(self):
        """This tests that _get_security_group_from_name
        returns a securoty group from an ID as expected.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_get_security_group_from_name', test_properties)
        current_ctx.set(ctx=ctx)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = \
                ec2_client.create_security_group('test_get_'
                                                 'security_group_from_name',
                                                 'this is test')
            ctx.instance.runtime_properties['aws_resource_id'] = group.id
            output = securitygroup._get_security_group_from_name(
                group.id)
            self.assertEqual(group.id, output.id)

    @mock_ec2
    def test_get_all_groups(self):
        """ This tests that all created groups are returned
        by _get_all_security_groups
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_get_all_groups', test_properties)
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_get_all_groups',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        output = securitygroup._get_all_security_groups(
            list_of_group_ids=group.id)
        self.assertEqual(output[0].id, group.id)

    @mock_ec2
    def test_create_group_rules_no_src_group_id_or_cidr(self):
        """ This tests that either src_group_id or cidr_ip is
        error is raised when both are given.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_group_rules_no_src_group_id_or_cidr',
            test_properties)
        current_ctx.set(ctx=ctx)
        del ctx.node.properties['rules'][0]['cidr_ip']
        group = ec2_client.create_security_group(
            'test_create_group_rules_no_src_group_id_or_cidr',
            'this is test')
        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._create_group_rules,
            group)
        self.assertIn(
            'You need to pass either src_group_id OR cidr_ip.',
            ex.message)

    @mock_ec2
    def test_create_group_rules_both_src_group_id_cidr(self):
        """ This tests that either src_group_id or cidr_ip is
        error is raised when neither is given.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(
            'test_create_group_rules_both_src_group_id_or_cidr',
            'this is test')
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_group_rules_both_src_group_id_or_cidr',
            test_properties)
        current_ctx.set(ctx=ctx)
        group_object = ec2_client.create_security_group(
            'dummy',
            'this is test')
        ctx.node.properties['rules'][0]['src_group_id'] = group_object
        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._create_group_rules,
            group)
        self.assertIn(
            'You need to pass either src_group_id OR cidr_ip.',
            ex.message)

    @mock_ec2
    def test_create_group_rules_src_group(self):
        """ This tests that _create_group_rules creates
        the rules and that they match on the way out
        to what when in.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_group_rules_src_group', test_properties)
        group_object = ec2_client.create_security_group(
            'dummy',
            'this is test')
        ctx.node.properties['rules'][0]['src_group_id'] = group_object.id
        del ctx.node.properties['rules'][0]['cidr_ip']
        current_ctx.set(ctx=ctx)
        group = ec2_client.create_security_group(
            'test_create_group_rules_src_group',
            'this is test')
        securitygroup._create_group_rules(group)
        self.assertEqual(
            str(group.rules),
            str(ec2_client.get_all_security_groups(
                groupnames='test_create_group_rules_src_group')[0].rules))

    @mock_ec2
    def test_create_external_securitygroup_not_external(self):
        """ This checks that _create_external_securitygroup
        returns false when use_external_resource is false.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_external_securitygroup_not_external',
            test_properties)
        current_ctx.set(ctx=ctx)

        name = ctx.node.properties['resource_id']
        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._create_external_securitygroup(
            name)
        self.assertEqual(False, output)

    @mock_ec2
    def test_delete_external_securitygroup_not_external(self):
        """ This checks that _delete_external_securitygroup
        returns false when use_external_resource is false.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_delete_external_securitygroup_not_external',
            test_properties)
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(False, output)
