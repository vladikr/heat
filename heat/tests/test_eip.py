# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import sys
import os

import nose
import unittest
import mox
import json

from nose.plugins.attrib import attr

from heat.engine.resources import eip
from heat.engine import parser
from heat.tests.v1_1 import fakes


@attr(tag=['unit', 'resource'])
@attr(speed='fast')
class EIPTest(unittest.TestCase):
    def setUp(self):
        self.m = mox.Mox()
        self.fc = fakes.FakeClient()
        self.m.StubOutWithMock(eip.ElasticIp, 'nova')
        self.m.StubOutWithMock(eip.ElasticIpAssociation, 'nova')
        self.m.StubOutWithMock(self.fc.servers, 'get')

    def tearDown(self):
        self.m.UnsetStubs()
        print "EIPTest teardown complete"

    def load_template(self):
        self.path = os.path.dirname(os.path.realpath(__file__)).\
            replace('heat/tests', 'templates')
        f = open("%s/WordPress_Single_Instance_With_EIP.template" % self.path)
        t = json.loads(f.read())
        f.close()
        return t

    def parse_stack(self, t):
        class DummyContext():
            tenant = 'test_tenant'
            username = 'test_username'
            password = 'password'
            auth_url = 'http://localhost:5000/v2.0'
        t['Parameters']['KeyName']['Value'] = 'test'
        stack = parser.Stack(DummyContext(), 'test_stack', parser.Template(t),
                             stack_id=-1)

        return stack

    def create_eip(self, t, stack, resource_name):
        resource = eip.ElasticIp(resource_name,
                                      t['Resources'][resource_name],
                                      stack)
        self.assertEqual(None, resource.validate())
        self.assertEqual(None, resource.create())
        self.assertEqual(eip.ElasticIp.CREATE_COMPLETE, resource.state)
        return resource

    def create_association(self, t, stack, resource_name):
        resource = eip.ElasticIpAssociation(resource_name,
                                      t['Resources'][resource_name],
                                      stack)
        self.assertEqual(None, resource.validate())
        self.assertEqual(None, resource.create())
        self.assertEqual(eip.ElasticIpAssociation.CREATE_COMPLETE,
                         resource.state)
        return resource

    def test_eip(self):

        eip.ElasticIp.nova().AndReturn(self.fc)
        eip.ElasticIp.nova().AndReturn(self.fc)

        self.m.ReplayAll()

        t = self.load_template()
        stack = self.parse_stack(t)
        resource = self.create_eip(t, stack, 'IPAddress')

        self.assertEqual('11.0.0.1', resource.FnGetRefId())
        resource.ipaddress = None
        self.assertEqual('11.0.0.1', resource.FnGetRefId())

        self.assertEqual('1', resource.FnGetAtt('AllocationId'))

        self.assertEqual(eip.ElasticIp.UPDATE_REPLACE,
                          resource.handle_update())

        try:
            resource.FnGetAtt('Foo')
            raise Exception('Expected InvalidTemplateAttribute')
        except eip.exception.InvalidTemplateAttribute:
            pass

        resource.delete()

        self.m.VerifyAll()

    def test_association(self):
        eip.ElasticIp.nova().AndReturn(self.fc)
        eip.ElasticIpAssociation.nova().AndReturn(self.fc)
        self.fc.servers.get('WebServer').AndReturn(self.fc.servers.list()[0])
        eip.ElasticIpAssociation.nova().AndReturn(self.fc)
        self.fc.servers.get('WebServer').AndReturn(self.fc.servers.list()[0])
        eip.ElasticIp.nova().AndReturn(self.fc)

        self.m.ReplayAll()

        t = self.load_template()
        stack = self.parse_stack(t)

        resource = self.create_eip(t, stack, 'IPAddress')
        association = self.create_association(t, stack, 'IPAssoc')

        # TODO sbaker, figure out why this is an empty string
        #self.assertEqual('', association.FnGetRefId())

        association.delete()
        resource.delete()

        self.m.VerifyAll()

    # allows testing of the test directly, shown below
    if __name__ == '__main__':
        sys.argv.append(__file__)
        nose.main()
