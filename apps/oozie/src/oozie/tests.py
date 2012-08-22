#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
  import json
except ImportError:
  import simplejson as json
import logging

from nose.plugins.skip import SkipTest
from nose.tools import assert_true, assert_false, assert_equal, assert_not_equal
from django.core.urlresolvers import reverse

from desktop.lib.django_test_util import make_logged_in_client
from desktop.lib.test_utils import grant_access
from liboozie import oozie_api
from liboozie.types import WorkflowList, Workflow as OozieWorkflow, Coordinator as OozieCoordinator,\
  CoordinatorList, WorkflowAction

from oozie.models import Workflow, Node, Job, Coordinator, Fork
from oozie.conf import SHARE_JOBS, REMOTE_DEPLOYMENT_DIR

LOG = logging.getLogger(__name__)



class MockOozieApi:
  JSON_WORKFLOW_LIST = [{u'status': u'RUNNING', u'run': 0, u'startTime': u'Mon, 30 Jul 2012 22:35:48 GMT', u'appName': u'WordCount1', u'lastModTime': u'Mon, 30 Jul 2012 22:37:00 GMT', u'actions': [], u'acl': None, u'appPath': None, u'externalId': None, u'consoleUrl': u'http://runreal:11000/oozie?job=0000012-120725142744176-oozie-oozi-W', u'conf': None, u'parentId': None, u'createdTime': u'Mon, 30 Jul 2012 22:35:48 GMT', u'toString': u'Workflow id[0000012-120725142744176-oozie-oozi-W] status[SUCCEEDED]', u'endTime': u'Mon, 30 Jul 2012 22:37:00 GMT', u'id': u'0000012-120725142744176-oozie-oozi-W', u'group': None, u'user': u'romain'},
                        {u'status': u'KILLED', u'run': 0, u'startTime': u'Mon, 30 Jul 2012 22:31:08 GMT', u'appName': u'WordCount2', u'lastModTime': u'Mon, 30 Jul 2012 22:32:20 GMT', u'actions': [], u'acl': None, u'appPath': None, u'externalId': None, u'consoleUrl': u'http://runreal:11000/oozie?job=0000011-120725142744176-oozie-oozi-W', u'conf': None, u'parentId': None, u'createdTime': u'Mon, 30 Jul 2012 22:31:08 GMT', u'toString': u'Workflow id[0000011-120725142744176-oozie-oozi-W] status[SUCCEEDED]', u'endTime': u'Mon, 30 Jul 2012 22:32:20 GMT', u'id': u'0000011-120725142744176-oozie-oozi-W', u'group': None, u'user': u'romain'},
                        {u'status': u'SUCCEEDED', u'run': 0, u'startTime': u'Mon, 30 Jul 2012 22:20:48 GMT', u'appName': u'WordCount3', u'lastModTime': u'Mon, 30 Jul 2012 22:22:00 GMT', u'actions': [], u'acl': None, u'appPath': None, u'externalId': None, u'consoleUrl': u'http://runreal:11000/oozie?job=0000009-120725142744176-oozie-oozi-W', u'conf': None, u'parentId': None, u'createdTime': u'Mon, 30 Jul 2012 22:20:48 GMT', u'toString': u'Workflow id[0000009-120725142744176-oozie-oozi-W] status[SUCCEEDED]', u'endTime': u'Mon, 30 Jul 2012 22:22:00 GMT', u'id': u'0000009-120725142744176-oozie-oozi-W', u'group': None, u'user': u'romain'},
                        {u'status': u'SUCCEEDED', u'run': 0, u'startTime': u'Mon, 30 Jul 2012 22:16:58 GMT', u'appName': u'WordCount4', u'lastModTime': u'Mon, 30 Jul 2012 22:18:10 GMT', u'actions': [], u'acl': None, u'appPath': None, u'externalId': None, u'consoleUrl': u'http://runreal:11000/oozie?job=0000008-120725142744176-oozie-oozi-W', u'conf': None, u'parentId': None, u'createdTime': u'Mon, 30 Jul 2012 22:16:58 GMT', u'toString': u'Workflow id[0000008-120725142744176-oozie-oozi-W] status[SUCCEEDED]', u'endTime': u'Mon, 30 Jul 2012 22:18:10 GMT', u'id': u'0000008-120725142744176-oozie-oozi-W', u'group': None, u'user': u'romain'}]
  WORKFLOW_IDS = [wf['id'] for wf in JSON_WORKFLOW_LIST]

  JSON_COORDINATOR_LIST = [{u'startTime': u'Sun, 01 Jul 2012 00:00:00 GMT', u'actions': [], u'frequency': 1, u'concurrency': 1, u'pauseTime': None, u'group': None, u'toString': u'Coornidator application id[0000041-120717205528122-oozie-oozi-C] status[DONEWITHERROR]', u'consoleUrl': None, u'mat_throttling': 0, u'status': u'DONEWITHERROR', u'conf': None, u'user': u'romain', u'timeOut': 120, u'coordJobPath': u'hdfs://localhost:8020/user/romain/demo2', u'timeUnit': u'DAY', u'coordJobId': u'0000041-120717205528122-oozie-oozi-C', u'coordJobName': u'DailyWordCount1', u'nextMaterializedTime': u'Wed, 04 Jul 2012 00:00:00 GMT', u'coordExternalId': None, u'acl': None, u'lastAction': u'Wed, 04 Jul 2012 00:00:00 GMT', u'executionPolicy': u'FIFO', u'timeZone': u'America/Los_Angeles', u'endTime': u'Wed, 04 Jul 2012 00:00:00 GMT'},
                           {u'startTime': u'Sun, 01 Jul 2012 00:00:00 GMT', u'actions': [], u'frequency': 1, u'concurrency': 1, u'pauseTime': None, u'group': None, u'toString': u'Coornidator application id[0000011-120706144403213-oozie-oozi-C] status[DONEWITHERROR]', u'consoleUrl': None, u'mat_throttling': 0, u'status': u'DONEWITHERROR', u'conf': None, u'user': u'romain', u'timeOut': 120, u'coordJobPath': u'hdfs://localhost:8020/user/hue/jobsub/_romain_-design-2', u'timeUnit': u'DAY', u'coordJobId': u'0000011-120706144403213-oozie-oozi-C', u'coordJobName': u'DailyWordCount2', u'nextMaterializedTime': u'Thu, 05 Jul 2012 00:00:00 GMT', u'coordExternalId': None, u'acl': None, u'lastAction': u'Thu, 05 Jul 2012 00:00:00 GMT', u'executionPolicy': u'FIFO', u'timeZone': u'America/Los_Angeles', u'endTime': u'Wed, 04 Jul 2012 18:54:00 GMT'},
                           {u'startTime': u'Sun, 01 Jul 2012 00:00:00 GMT', u'actions': [], u'frequency': 1, u'concurrency': 1, u'pauseTime': None, u'group': None, u'toString': u'Coornidator application id[0000010-120706144403213-oozie-oozi-C] status[DONEWITHERROR]', u'consoleUrl': None, u'mat_throttling': 0, u'status': u'DONEWITHERROR', u'conf': None, u'user': u'romain', u'timeOut': 120, u'coordJobPath': u'hdfs://localhost:8020/user/hue/jobsub/_romain_-design-2', u'timeUnit': u'DAY', u'coordJobId': u'0000010-120706144403213-oozie-oozi-C', u'coordJobName': u'DailyWordCount3', u'nextMaterializedTime': u'Thu, 05 Jul 2012 00:00:00 GMT', u'coordExternalId': None, u'acl': None, u'lastAction': u'Thu, 05 Jul 2012 00:00:00 GMT', u'executionPolicy': u'FIFO', u'timeZone': u'America/Los_Angeles', u'endTime': u'Wed, 04 Jul 2012 18:54:00 GMT'},
                           {u'startTime': u'Sun, 01 Jul 2012 00:00:00 GMT', u'actions': [], u'frequency': 1, u'concurrency': 1, u'pauseTime': None, u'group': None, u'toString': u'Coornidator application id[0000009-120706144403213-oozie-oozi-C] status[DONEWITHERROR]', u'consoleUrl': None, u'mat_throttling': 0, u'status': u'DONEWITHERROR', u'conf': None, u'user': u'romain', u'timeOut': 120, u'coordJobPath': u'hdfs://localhost:8020/user/hue/jobsub/_romain_-design-2', u'timeUnit': u'DAY', u'coordJobId': u'0000009-120706144403213-oozie-oozi-C', u'coordJobName': u'DailyWordCount4', u'nextMaterializedTime': u'Thu, 05 Jul 2012 00:00:00 GMT', u'coordExternalId': None, u'acl': None, u'lastAction': u'Thu, 05 Jul 2012 00:00:00 GMT', u'executionPolicy': u'FIFO', u'timeZone': u'America/Los_Angeles', u'endTime': u'Wed, 04 Jul 2012 18:54:00 GMT'}]
  COORDINATOR_IDS = [coord['coordJobId'] for coord in JSON_COORDINATOR_LIST]

  WORKFLOW_ACTION = {u'status': u'OK', u'retries': 0, u'transition': u'end', u'stats': None, u'startTime': u'Fri, 10 Aug 2012 05:24:21 GMT', u'toString': u'Action name[WordCount] status[OK]', u'cred': u'null', u'errorMessage': None, u'errorCode': None, u'consoleUrl': u'http://localhost:50030/jobdetails.jsp?jobid=job_201208072118_0044', u'externalId': u'job_201208072118_0044', u'externalStatus': u'SUCCEEDED', u'conf': u'<map-reduce xmlns="uri:oozie:workflow:0.2">\r\n  <job-tracker>localhost:8021</job-tracker>\r\n  <name-node>hdfs://localhost:8020</name-node>\r\n  <configuration>\r\n    <property>\r\n      <name>mapred.mapper.regex</name>\r\n      <value>dream</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.input.dir</name>\r\n      <value>/user/romain/words/20120702</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.output.dir</name>\r\n      <value>/user/romain/out/rrwords/20120702</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.mapper.class</name>\r\n      <value>org.apache.hadoop.mapred.lib.RegexMapper</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.combiner.class</name>\r\n      <value>org.apache.hadoop.mapred.lib.LongSumReducer</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.reducer.class</name>\r\n      <value>org.apache.hadoop.mapred.lib.LongSumReducer</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.output.key.class</name>\r\n      <value>org.apache.hadoop.io.Text</value>\r\n    </property>\r\n    <property>\r\n      <name>mapred.output.value.class</name>\r\n      <value>org.apache.hadoop.io.LongWritable</value>\r\n    </property>\r\n  </configuration>\r\n</map-reduce>', u'type': u'map-reduce', u'trackerUri': u'localhost:8021', u'externalChildIDs': None, u'endTime': u'Fri, 10 Aug 2012 05:24:38 GMT', u'data': None, u'id': u'0000021-120807211836060-oozie-oozi-W@WordCount', u'name': u'WordCount'}

  def __init__(self, *args, **kwargs):
    pass

  def setuser(self, user):
    pass

  def submit_job(self, properties):
    return 'ONE-OOZIE-ID'

  def get_workflows(self, **kwargs):
    return WorkflowList(self, {'offset': 0, 'total': 4, 'workflows': MockOozieApi.JSON_WORKFLOW_LIST})

  def get_coordinators(self, **kwargs):
    return CoordinatorList(self, {'offset': 0, 'total': 5, 'coordinatorjobs': MockOozieApi.JSON_COORDINATOR_LIST})

  def get_job(self, job_id):
    return OozieWorkflow(self, MockOozieApi.JSON_WORKFLOW_LIST[0])

  def get_coordinator(self, job_id):
    return OozieCoordinator(self, MockOozieApi.JSON_COORDINATOR_LIST[0])

  def get_action(self, action_id):
    return WorkflowAction(MockOozieApi.WORKFLOW_ACTION)

  def job_control(self, job_id, action):
    return 'Done'

  def get_job_definition(self, jobid):
    return '<xml></xml>'

  def get_job_log(self, jobid):
    return '<xml></xml>'


# Monkey patch Lib Oozie with Mock API
oozie_api.OozieApi = MockOozieApi



class TestEditor:

  def setUp(self):
    Workflow.objects.all().delete()
    Coordinator.objects.all().delete()

    self.c = make_logged_in_client()
    self.wf = create_workflow()


  def test_find_parameters(self):
    jobs = [Job(name="$a"),
            Job(name="foo ${b} $$"),
            Job(name="${foo}", description="xxx ${foo}")]

    result = [job.find_parameters(['name', 'description']) for job in jobs]
    assert_equal(set(["b", "foo"]), reduce(lambda x, y: x | set(y), result, set()))


  def test_create_workflow(self):
    # Done in the setUp
    pass


  def test_move_up(self):
    action1 = Node.objects.get(name='action-name-1')
    action2 = Node.objects.get(name='action-name-2')
    action3 = Node.objects.get(name='action-name-3')

    # 1
    # 2
    # 3
    move_up(self.c, self.wf, action2)
    move_up(self.c, self.wf, action3)

    # 1 2
    # 3
    move_up(self.c, self.wf, action1)
    move_up(self.c, self.wf, action2)

    # 1
    # 2
    # 3
    move_up(self.c, self.wf, action2)

    # 1 2
    #  3
    action4 = add_action(self.wf.id, action2.id, 'name-4')
    move_up(self.c, self.wf, action4)

    # 1 2 3 4


  def test_move_down(self):
    action1 = Node.objects.get(name='action-name-1')
    action2 = Node.objects.get(name='action-name-2')
    action3 = Node.objects.get(name='action-name-3')

    # 1
    # 2
    # 3
    move_down(self.c, self.wf, action1)
    move_down(self.c, self.wf, action2)

    # 1
    # 2
    # 3
    move_down(self.c, self.wf, action2)
    move_down(self.c, self.wf, action1)

    # 1 2 3
    move_down(self.c, self.wf, action3)
    move_down(self.c, self.wf, action2)

    # 1
    # 2 3
    action4 = add_action(self.wf.id, action2.id, 'name-4')

    #  1
    # 2 3
    # 4
    move_down(self.c, self.wf, action4)
    move_down(self.c, self.wf, action3)
    move_down(self.c, self.wf, action4)

    # 1
    # 2
    # 3
    # 4


  def test_clone_workflow(self):
    workflow_count = Workflow.objects.count()

    response = self.c.post(reverse('oozie:clone_workflow', args=[self.wf.id]), {}, follow=True)

    assert_equal(workflow_count + 1, Workflow.objects.count(), response)

    wf2 = Workflow.objects.latest('id')
    assert_not_equal(self.wf.id, wf2.id)
    assert_equal(self.wf.node_set.count(), wf2.node_set.count())

    node_ids = set(self.wf.node_set.values_list('id', flat=True))
    for node in wf2.node_set.all():
      assert_false(node.id in node_ids)

    raise SkipTest
    # To Fix
    assert_not_equal(self.wf.deployment_dir, wf2.deployment_dir)


  def test_clone_action(self):
    # Need to be tested in edit:workflow too
    action1 = Node.objects.get(name='action-name-1')

    node_count = self.wf.actions.count()
    assert_true(1, len(action1.get_children()))

    response = self.c.post(reverse('oozie:clone_action', args=[action1.id]), {}, follow=True)

    assert_not_equal(action1.id, action1.get_children()[1].id)
    assert_true(2, len(action1.get_children()))
    assert_equal(node_count + 1, self.wf.actions.count())


  def test_decision_node(self):
    action1 = Node.objects.get(name='action-name-1')
    action2 = Node.objects.get(name='action-name-2')
    action3 = Node.objects.get(name='action-name-3')

    move_down(self.c, self.wf, action1)
    fork = action1.get_parent()

    # 1 2
    #  3
    response = self.c.get(reverse('oozie:edit_workflow_fork', args=[fork.id]), {}, follow=True)
    assert_equal(200, response.status_code)

    assert_false(fork.has_decisions())

    # Missing information for converting to decision
    response = self.c.post(reverse('oozie:edit_workflow_fork', args=[fork.id]), {
        u'form-MAX_NUM_FORMS': [u'0'], u'form-TOTAL_FORMS': [u'2'], u'form-INITIAL_FORMS': [u'2'],
        u'form-0-comment': [u''], u'form-0-id': [u'%s' % action1.id],
        u'form-1-comment': [u''], u'form-1-id': [u'%s' % action2.id],
        u'child': [u'%s' % self.wf.end.id]}, follow=True)
    assert_true('This field is required' in response.content, response.content)
    assert_equal(200, response.status_code)
    assert_false(fork.has_decisions())

    # Convert to decision
    response = self.c.post(reverse('oozie:edit_workflow_fork', args=[fork.id]), {
        u'form-MAX_NUM_FORMS': [u'0'], u'form-TOTAL_FORMS': [u'2'], u'form-INITIAL_FORMS': [u'2'],
        u'form-0-comment': [u'output'], u'form-0-id': [u'%s' % action1.id],
        u'form-1-comment': [u'output'], u'form-1-id': [u'%s' % action2.id],
        u'child': [u'%s' % self.wf.end.id]}, follow=True)
    assert_equal(200, response.status_code)

    raise SkipTest
    # Mystery below, link_formset.save() does not appear to save the links during a test
    assert_equal(Fork.ACTION_DECISION_TYPE, fork.node_type)
    assert_true(fork.has_decisions(), response.content)


  def test_workflow_gen_xml(self):
    assert_equal(
        '<workflow-app name="wf-name-1" xmlns="uri:oozie:workflow:0.2">\n'
        '    <start to="action-name-1"/>\n'
        '    <action name="action-name-1">\n'
        '        <map-reduce>\n'
        '           <job-tracker>${jobTracker}</job-tracker>\n'
        '            <name-node>${nameNode}</name-node>\n'
        '        </map-reduce>\n'
        '        <ok to="action-name-2"/>\n'
        '        <error to="kill"/>\n'
        '    </action>\n'
        '    <action name="action-name-2">\n'
        '        <map-reduce>\n'
        '            <job-tracker>${jobTracker}</job-tracker>\n'
        '            <name-node>${nameNode}</name-node>\n'
        '        </map-reduce>\n'
        '        <ok to="action-name-3"/>\n'
        '        <error to="kill"/>\n'
        '    </action>\n'
        '    <action name="action-name-3">\n'
        '        <map-reduce>\n'
        '            <job-tracker>${jobTracker}</job-tracker>\n'
        '            <name-node>${nameNode}</name-node>\n'
        '        </map-reduce>\n'
        '        <ok to="end"/>\n'
        '        <error to="kill"/>\n'
        '    </action>\n'
        '    <kill name="kill">\n'
        '        <message>Action failed, error message[${wf:errorMessage(wf:lastErrorNode())}]</message>\n'
        '    </kill>\n'
        '    <end name="end"/>\n'
        '</workflow-app>'.split(), self.wf.to_xml().split())


  def test_edit_workflow(self):
    response = self.c.get(reverse('oozie:edit_workflow', args=[self.wf.id]))
    assert_true('Editor' in response.content, response.content)
    assert_true('Workflow wf-name-1' in response.content, response.content)

    # Edit
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = self.c.post(reverse('oozie:edit_workflow', args=[self.wf.id]), {})
      assert_true('jHueNotify.error' in response.content, response.content)
    finally:
      finish()

    # Build POST dict from the forms and test this
    raise SkipTest

    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = self.c.post(reverse('oozie:edit_workflow', args=[self.wf.id]), WORKFLOW_DICT)
      assert_false('jHueNotify.error' in response.content, response.content)
    finally:
      finish()


  def test_workflow_permissions(self):
    response = self.c.get(reverse('oozie:edit_workflow', args=[self.wf.id]))
    assert_true('Editor' in response.content, response.content)
    assert_true('Workflow wf-name-1' in response.content, response.content)
    assert_false(self.wf.is_shared)

    # Login as someone else
    client_not_me = make_logged_in_client(username='not_me', is_superuser=False, groupname='test')
    grant_access("not_me", "test", "oozie")

    # List
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:list_workflows'))
      assert_false('wf-name-1' in response.content, response.content)
    finally:
      finish()
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.get(reverse('oozie:list_workflows'))
      assert_false('wf-name-1' in response.content, response.content)
    finally:
      finish()

    # View
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:edit_workflow', args=[self.wf.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.get(reverse('oozie:edit_workflow', args=[self.wf.id]))
      assert_equal(200, response.status_code)
      assert_false('wf-name-1' in response.content, response.content)
    finally:
      finish()

    # Share it !
    self.wf.is_shared = True
    self.wf.save()

    # List
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:list_workflows'))
      assert_equal(200, response.status_code)
      assert_true('wf-name-1' in response.content, response.content)
    finally:
      finish()

    # Edit
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.post(reverse('oozie:edit_workflow', args=[self.wf.id]))
      assert_true('Not allowed' in response.content, response.content)
    finally:
      finish()

    # Submit
    finish = SHARE_JOBS.set_for_testing(False)
    finish_deployement = REMOTE_DEPLOYMENT_DIR.set_for_testing('/tmp')
    try:
      response = client_not_me.post(reverse('oozie:submit_workflow', args=[self.wf.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()
      finish_deployement()
    finish = SHARE_JOBS.set_for_testing(True)
    finish_deployement = REMOTE_DEPLOYMENT_DIR.set_for_testing('/tmp')
    try:
      response = client_not_me.post(reverse('oozie:submit_workflow', args=[self.wf.id]))
      assert_false('Permission denied' in response.content, response.content)
    finally:
      finish()
      finish_deployement()

    # Delete
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.post(reverse('oozie:delete_workflow', args=[self.wf.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()

    response = self.c.post(reverse('oozie:delete_workflow', args=[self.wf.id]), follow=True)
    assert_equal(200, response.status_code)


  def test_clone_coordinator(self):
    coord = create_coordinator(self.wf)
    coordinator_count = Coordinator.objects.count()

    response = self.c.post(reverse('oozie:clone_coordinator', args=[coord.id]), {}, follow=True)

    wf2 = Coordinator.objects.latest('id')
    assert_not_equal(coord.id, wf2.id)
    assert_equal(coordinator_count + 1, Coordinator.objects.count(), response)

    assert_equal(coord.dataset_set.count(), wf2.dataset_set.count())
    assert_equal(coord.datainput_set.count(), wf2.datainput_set.count())
    assert_equal(coord.dataoutput_set.count(), wf2.dataoutput_set.count())

    ds_ids = set(coord.dataset_set.values_list('id', flat=True))
    for node in wf2.dataset_set.all():
      assert_false(node.id in ds_ids)

    data_input_ids = set(coord.datainput_set.values_list('id', flat=True))
    for node in wf2.datainput_set.all():
      assert_false(node.id in data_input_ids)

    data_output_ids = set(coord.dataoutput_set.values_list('id', flat=True))
    for node in wf2.dataoutput_set.all():
      assert_false(node.id in data_output_ids)


  def test_coordinator_permissions(self):
    coord = create_coordinator(self.wf)

    response = self.c.get(reverse('oozie:edit_coordinator', args=[coord.id]))
    assert_true('Editor' in response.content, response.content)

    # Edit
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = self.c.post(reverse('oozie:edit_coordinator', args=[coord.id]))
      assert_true('MyCoord' in response.content, response.content)
      assert_false('Permission denied' in response.content, response.content)
    finally:
      finish()

    # Login as someone else
    client_not_me = make_logged_in_client(username='not_me', is_superuser=False, groupname='test')
    grant_access("not_me", "test", "oozie")

    # List
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:list_coordinator'))
      assert_false('MyCoord' in response.content, response.content)
    finally:
      finish()
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.get(reverse('oozie:list_coordinator'))
      assert_false('MyCoord' in response.content, response.content)
    finally:
      finish()

    # View
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:edit_coordinator', args=[coord.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.get(reverse('oozie:edit_coordinator', args=[coord.id]))
      assert_false('MyCoord' in response.content, response.content)
    finally:
      finish()

    # Share it !
    coord.is_shared = True
    coord.save()
    coord.workflow.is_shared = True
    coord.workflow.save()

    # List
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.get(reverse('oozie:list_coordinator'))
      assert_equal(200, response.status_code)
      assert_true('MyCoord' in response.content, response.content)
    finally:
      finish()

    # Edit
    finish = SHARE_JOBS.set_for_testing(True)
    try:
      response = client_not_me.post(reverse('oozie:edit_coordinator', args=[coord.id]))
      assert_false('MyCoord' in response.content, response.content)
      assert_true('Not allowed' in response.content, response.content)
    finally:
      finish()

    # Submit
    finish = SHARE_JOBS.set_for_testing(False)
    finish_deployement = REMOTE_DEPLOYMENT_DIR.set_for_testing('/tmp')
    try:
      response = client_not_me.post(reverse('oozie:submit_coordinator', args=[coord.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()
      finish_deployement()
    finish = SHARE_JOBS.set_for_testing(True)
    finish_deployement = REMOTE_DEPLOYMENT_DIR.set_for_testing('/tmp')
    try:
      response = client_not_me.post(reverse('oozie:submit_coordinator', args=[coord.id]))
      assert_false('Permission denied' in response.content, response.content)
    finally:
      finish()
      finish_deployement()

    # Delete
    finish = SHARE_JOBS.set_for_testing(False)
    try:
      response = client_not_me.post(reverse('oozie:delete_coordinator', args=[coord.id]))
      assert_true('Permission denied' in response.content, response.content)
    finally:
      finish()

    response = self.c.post(reverse('oozie:delete_coordinator', args=[coord.id]), follow=True)
    assert_equal(200, response.status_code)


  def test_coordinator_gen_xml(self):
    coord = create_coordinator(self.wf)

    assert_equal(
        '<coordinator-app name="MyCoord"\n'
        '  frequency="${coord:days(1)}"\n'
        '  start="2012-07-01T00:00Z" end="2012-07-04T00:00Z" timezone="America/Los_Angeles"\n'
        '  xmlns="uri:oozie:coordinator:0.1">\n'
        '  <!--\n'
        '  <controls>\n'
        '    <timeout>[TIME_PERIOD]</timeout>\n'
        '    <concurrency>[CONCURRENCY]</concurrency>\n'
        '    <execution>[EXECUTION_STRATEGY]</execution>\n'
        '  </controls>\n'
        '  -->\n'
        '  <action>\n'
        '    <workflow>\n'
        '      <app-path>${wf_application_path}</app-path>\n'
        '      <configuration>\n'
        '     </configuration>\n'
        '   </workflow>\n'
        '  </action>\n'
        '</coordinator-app>\n'.split(), coord.to_xml().split())


  def test_create_coordinator_dataset(self):
    coord = create_coordinator(self.wf)
    create_dataset(coord)


  def test_create_coordinator_input_data(self):
    coord = create_coordinator(self.wf)
    create_dataset(coord)

    response = self.c.post(reverse('oozie:create_coordinator_data', args=[coord.id, 'input']),
                           {u'name': [u'input_dir'], u'dataset': [u'1']})
    data = json.loads(response.content)
    assert_equal(0, data['status'], data['data'])

  def test_install_examples(self):
    self.c.post(reverse('oozie:install_examples'))


# Utils
WORKFLOW_DICT = {u'deployment_dir': [u''], u'name': [u'wf-name-1'], u'description': [u'']}


# Beware: client not consistent with self.c in TestEditor
def add_action(workflow, action, name):
  c = make_logged_in_client()

  response = c.post("/oozie/new_action/%s/%s/%s" % (workflow, 'mapreduce', action), {
     u'files': [u'[]'], u'name': [name], u'jar_path': [u'/tmp/.file.jar'], u'job_properties': [u'[]'], u'archives': [u'[]'], u'description': [u'']}, follow=True)
  assert_equal(200, response.status_code)
  assert_true(Node.objects.filter(name=name).exists(), response)
  return Node.objects.get(name=name)


def create_workflow():
  c = make_logged_in_client()

  workflow_count = Workflow.objects.count()
  response = c.get(reverse('oozie:create_workflow'))
  assert_equal(workflow_count, Workflow.objects.count(), response)

  response = c.post(reverse('oozie:create_workflow'), WORKFLOW_DICT, follow=True)
  assert_equal(200, response.status_code)
  assert_equal(workflow_count + 1, Workflow.objects.count(), response)

  wf = Workflow.objects.get()
  assert_not_equal('', wf.deployment_dir)

  action1 = add_action(wf.id, wf.start.id, 'action-name-1')
  action2 = add_action(wf.id, action1.id, 'action-name-2')
  action3 = add_action(wf.id, action2.id, 'action-name-3')

  return wf


def create_coordinator(workflow):
  c = make_logged_in_client()

  coord_count = Coordinator.objects.count()
  response = c.get(reverse('oozie:create_coordinator'))
  assert_equal(coord_count, Coordinator.objects.count(), response)

  response = c.post(reverse('oozie:create_coordinator'), {u'end': [u'2012-07-04 00:00:00'], u'name': [u'MyCoord'], u'frequency_number': [u'1'], u'workflow': [workflow.id], u'frequency_unit': [u'days'], u'start': [u'2012-07-01 00:00:00'], u'timezone': [u'America/Los_Angeles'], u'description': [u'']})
  assert_equal(coord_count + 1, Coordinator.objects.count(), response)

  return Coordinator.objects.get()


def create_dataset(coord):
  c = make_logged_in_client()

  response = c.post(reverse('oozie:create_coordinator_dataset', args=[coord.id]),
                         {u'name': [u'MyDataset'], u'frequency_number': [u'1'], u'frequency_unit': [u'days'],
                          u'uri': [u'/data/${YEAR}${MONTH}${DAY}'], u'start': [u'2012-08-15'],
                          u'timezone': [u'America/Los_Angeles'], u'done_flag': [u''],
                          u'description': [u'']})
  data = json.loads(response.content)
  assert_equal(0, data['status'], data['data'])


def move(c, wf, direction, action):
  try:
    LOG.info(wf.get_hierarchy())
    LOG.info('%s %s' % (direction, action))
    assert_equal(200, c.post(reverse(direction, args=[action.id]), {}, follow=True).status_code)
  except:
    raise


def move_up(c, wf, action):
  move(c, wf, 'oozie:move_up_action', action)


def move_down(c, wf, action):
  move(c, wf, 'oozie:move_down_action', action)



class TestDashboard:

  def setUp(self):
    Workflow.objects.all().delete()
    Coordinator.objects.all().delete()

    self.c = make_logged_in_client()
    self.wf = create_workflow()


  def test_list_workflows(self):
    response = self.c.get(reverse('oozie:list_oozie_workflows'))
    for wf_id in MockOozieApi.WORKFLOW_IDS:
      assert_true(wf_id in response.content, response.content)


  def test_list_coordinators(self):
    response = self.c.get(reverse('oozie:list_oozie_coordinators'))
    for coord_id in MockOozieApi.COORDINATOR_IDS:
      assert_true(coord_id in response.content, response.content)


  def test_list_workflow(self):
    response = self.c.get(reverse('oozie:list_oozie_workflow', args=[MockOozieApi.WORKFLOW_IDS[0]]))
    assert_true('Workflow WordCount1' in response.content, response.content)
    assert_true('Workflow' in response.content, response.content)

    response = self.c.get(reverse('oozie:list_oozie_workflow', args=[MockOozieApi.WORKFLOW_IDS[0], MockOozieApi.COORDINATOR_IDS[0]]))
    assert_true('Workflow WordCount1' in response.content, response.content)
    assert_true('Workflow' in response.content, response.content)
    assert_true('DailyWordCount1' in response.content, response.content)
    assert_true('Coordinator' in response.content, response.content)


  def test_list_coordinator(self):
    response = self.c.get(reverse('oozie:list_oozie_coordinator', args=[MockOozieApi.COORDINATOR_IDS[0]]))
    assert_true('Coordinator DailyWordCount1' in response.content, response.content)
    assert_true('Workflow' in response.content, response.content)


  def test_manage_oozie_jobs(self):
    try:
      self.c.get(reverse('oozie:manage_oozie_jobs', args=[MockOozieApi.COORDINATOR_IDS[0], 'kill']))
      assert False
    except:
      pass

    response = self.c.post(reverse('oozie:manage_oozie_jobs', args=[MockOozieApi.COORDINATOR_IDS[0], 'kill']))
    data = json.loads(response.content)
    assert_equal(0, data['status'])


  def test_workflow_permissions(self):
    response = self.c.get(reverse('oozie:list_oozie_workflow', args=[MockOozieApi.WORKFLOW_IDS[0]]))
    assert_true('WordCount1' in response.content, response.content)
    assert_false('Permission denied' in response.content, response.content)

    response = self.c.get(reverse('oozie:list_oozie_workflow_action', args=['XXX']))
    assert_false('Permission denied' in response.content, response.content)

    # Login as someone else
    client_not_me = make_logged_in_client(username='not_me', is_superuser=False, groupname='test')
    grant_access("not_me", "test", "oozie")

    response = client_not_me.get(reverse('oozie:list_oozie_workflow', args=[MockOozieApi.WORKFLOW_IDS[0]]))
    assert_true('Permission denied' in response.content, response.content)

    response = client_not_me.get(reverse('oozie:list_oozie_workflow_action', args=['XXX']))
    assert_true('Permission denied' in response.content, response.content)


  def test_coordinator_permissions(self):
    response = self.c.get(reverse('oozie:list_oozie_coordinator', args=[MockOozieApi.COORDINATOR_IDS[0]]))
    assert_true('DailyWordCount1' in response.content, response.content)
    assert_false('Permission denied' in response.content, response.content)

    # Login as someone else
    client_not_me = make_logged_in_client(username='not_me', is_superuser=False, groupname='test')
    grant_access("not_me", "test", "oozie")

    response = client_not_me.get(reverse('oozie:list_oozie_coordinator', args=[MockOozieApi.COORDINATOR_IDS[0]]))
    assert_true('Permission denied' in response.content, response.content)

