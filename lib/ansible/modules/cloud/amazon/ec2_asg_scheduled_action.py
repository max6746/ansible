#!/usr/bin/python
# (c) 2016, Mike Mochan <@mmochan>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
# A Munro: 16 Dec 2018
# Was not working on ansible 2.7, so updated to work, including full state present/absent
# and reporting changes. More flexibility on settings that can be set in the playbook, etc.
#

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
module: ec2_asg_scheduled_action
short_description: create, modify and delete AutoScaling Scheduled Actions.
description:
  - Read the AWS documentation for Scheduled Actions
    U(http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-as-scheduledaction.html
version_added: "2.8"
requirements: [ "boto3", "botocore" ]
options:
  autoscaling_group_name:
    description:
      - The name of the autoscaling group.
    required: true
  scheduled_action_name:
    description:
      - The name of the scheduled action.
    required: true
  state:
    description:
      - Whether the schedule is present or absent.
    required: false
    default: present
    choices: ['present', 'absent']
  desired_capacity:
    description:
      - The number of EC2 instances that should be running in the group.
    required: true
  recurrence:
    description:
      - The recurring schedule for this action, in Unix cron syntax format.
    required: true
  min_size:
    description:
      - Minimum number of instances in group.
  max_size:
    description:
      - Maximum number of instances in group.
  start_time:
    description:
      - The time for the scheduled action to start.
  end_time:
    description:
      - The time for the recurring schedule to end.
author: Mike Mochan(@mmochan)
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Create a scheduled action for my autoscaling group.
- name: create a scheduled action for autoscaling group
  ec2_asg_scheduled_action:
    autoscaling_group_name: test_asg
    scheduled_action_name: mtest_asg_schedule
    start_time: 2017 August 18 08:00 UTC+10
    end_time: 2018 August 18 08:00 UTC+10
    recurrence: 40 22 * * 1-5
    min_size: 0
    max_size: 0
    desired_capacity: 0
    state: present
  register: scheduled_action

'''

RETURN = '''
task:
  description: The result of the present, and absent actions.
  returned: success
  type: dict
'''

try:
    from botocore.exceptions import ClientError
except ImportError:
    pass  # caught by imported HAS_BOTO3

from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.ec2 import (get_aws_connection_info, boto3_conn, ec2_argument_spec,
                                      camel_dict_to_snake_dict, AWSRetry, HAS_BOTO3)


def get_common_params(module):
    params = dict()
    params['aws_retry'] = True
    params['AutoScalingGroupName'] = module.params.get('autoscaling_group_name')
    params['ScheduledActionName'] = module.params.get('scheduled_action_name')

    return params


def delete_scheduled_action(client, module):
    changed = False
    existing = describe_scheduled_actions(client, module)

    if "ScheduledUpdateGroupActions" not in existing:
        return changed, actions

    actions = existing.get("ScheduledUpdateGroupActions")

    if len(actions) == 0:
        return changed, actions

    changed = True
    params = dict()
    params = get_common_params(module)

    try:
        actions = client.delete_scheduled_action(**params)
    except ClientError as e:
        module.fail_json(msg=str(e))

    return changed, actions


def describe_scheduled_actions(client, module):
    actions = dict()
    params = get_common_params(module)
    params['ScheduledActionNames'] = [params.pop('ScheduledActionName')]
    try:
        actions = client.describe_scheduled_actions(**params)
    except ClientError as e:
        pass

    return actions


def put_scheduled_update_group_action(client, module):
    changed = False
    params = get_common_params(module)

    params['Recurrence'] = module.params.get('recurrence')
    params['DesiredCapacity'] = module.params.get('desired_capacity')

    # Some of these are optional
    if module.params.get('min_size') is not None:
        params['MinSize'] = module.params.get('min_size')

    if module.params.get('max_size') is not None:
        params['MaxSize'] = module.params.get('max_size')

    if module.params.get('start_time') is not None:
        params['StartTime'] = module.params.get('start_time')

    if module.params.get('end_time') is not None:
        params['EndTime'] = module.params.get('end_time')

    existing = describe_scheduled_actions(client, module)
    actions = existing.get("ScheduledUpdateGroupActions")

    try:
        status = client.put_scheduled_update_group_action(**params)
    except ClientError as e:
        module.fail_json(msg=str(e))

    if len(actions) == 0:
        changed = True
    else:
        existing = describe_scheduled_actions(client, module)
        updated = existing.get("ScheduledUpdateGroupActions")[0]

        if actions[0] != updated:
            changed = True

    return changed, status


def main():
    argument_spec = dict(
        autoscaling_group_name=dict(default=None),
        scheduled_action_name=dict(default=None),
        start_time=dict(default=None),
        end_time=dict(default=None),
        recurrence=dict(default=None),
        min_size=dict(default=None, type='int'),
        max_size=dict(default=None, type='int'),
        desired_capacity=dict(default=None, type='int'),
        state=dict(default='present', choices=['present', 'absent'])
    )

    module = AnsibleAWSModule(argument_spec=argument_spec)

    if not HAS_BOTO3:
        module.fail_json(msg='json and boto3 required for this module')

    try:
        client = module.client('autoscaling', retry_decorator=AWSRetry.jittered_backoff())
    except ClientError as e:
        module.fail_json(msg=e.message, **camel_dict_to_snake_dict(e.response))

    state = module.params.get('state')

    if state == 'present':
        (changed, results) = put_scheduled_update_group_action(client, module)
        module.exit_json(changed=changed, results=results)
    else:
        (changed, results) = delete_scheduled_action(client, module)
        module.exit_json(changed=changed, results=results)


if __name__ == '__main__':
    main()
