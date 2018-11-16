#!/usr/bin/python

# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: iam_user_facts
short_description: Gather IAM user(s) facts in AWS
description:
  - This module can be used to gather IAM user(s) facts in AWS.
version_added: "2.8"
author:
  - Constantin Bugneac (@Constantin07)
  - Abhijeet Kasurde (@Akasurde)
options:
  name:
    description:
     - The name of the IAM user to look for.
    required: false
    type: str
  group:
    description:
     - The group name name of the IAM user to look for. Mutually exclusive with C(path).
    required: false
    type: str
  path:
    description:
     - The path to the IAM user. Mutually exclusive with C(group).
     - If specified, then would get all user names whose path starts with user provided value.
    required: false
    default: '/'
    type: str
requirements:
  - botocore
  - boto3
extends_documentation_fragment:
  - aws
  - ec2
'''

EXAMPLES = r'''
# Note: These examples do not set authentication details, see the AWS Guide for details.
# Gather facts about "test" user.
- name: Get IAM user facts
  iam_user_facts:
    name: "test"

# Gather facts about all users in the "dev" group.
- name: Get IAM user facts
  iam_user_facts:
    group: "dev"

# Gather facts about all users with "/division_abc/subdivision_xyz/" path.
- name: Get IAM user facts
  iam_user_facts:
    path: "/division_abc/subdivision_xyz/"
'''

RETURN = r'''
arn:
    description: the ARN of the user
    returned: if user exists
    type: string
    sample: "arn:aws:iam::156360693172:user/dev/test_user"
create_date:
    description: the datetime user was created
    returned: if user exists
    type: string
    sample: "2016-05-24T12:24:59+00:00"
password_last_used:
    description: the last datetime the password was used by user
    returned: if password was used at least once
    type: string
    sample: "2016-05-25T13:39:11+00:00"
path:
    description: the path to user
    returned: if user exists
    type: string
    sample: "/dev/"
user_id:
    description: the unique user id
    returned: if user exists
    type: string
    sample: "AIDUIOOCQKTUGI6QJLGH2"
user_name:
    description: the user name
    returned: if user exists
    type: string
    sample: "test_user"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import boto3_conn, camel_dict_to_snake_dict, ec2_argument_spec, get_aws_connection_info

try:
    import boto3
    from botocore.exceptions import ClientError, ParamValidationError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


def list_iam_users(connection, module):

    name = module.params.get('name')
    group = module.params.get('group')
    path = module.params.get('path')

    params = dict(MaxItems=1000)
    iam_users = []

    if name and not path:
        params['UserName'] = name
        try:
            iam_users.append(connection.get_user(**params)['User'])
        except (ClientError, ParamValidationError) as e:
            module.fail_json(msg=e.message, **camel_dict_to_snake_dict(e.response))

    if group:
        params['GroupName'] = group
        try:
            iam_users = connection.get_group(**params)['Users']
        except (ClientError, ParamValidationError) as e:
            module.fail_json(msg="Failed while listing IAM groups %s " % e.message,
                             **camel_dict_to_snake_dict(e.response))
        if name:
            iam_users = [user for user in iam_users if user['UserName'] == name]

    if path and not group:
        params['PathPrefix'] = path
        try:
            iam_users = connection.list_users(**params)['Users']
        except (ClientError, ParamValidationError) as e:
            module.fail_json(msg="Failed while listing IAM users %s " % e.message,
                             **camel_dict_to_snake_dict(e.response))
        if name:
            iam_users = [user for user in iam_users if user['UserName'] == name]

    module.exit_json(iam_users=[camel_dict_to_snake_dict(user) for user in iam_users])


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            name=dict(),
            group=dict(),
            path=dict(default='/')
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[
            ['group', 'path']
        ],
        supports_check_mode=True
    )

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 required for this module')

    region, ec2_url, aws_connect_params = get_aws_connection_info(module, boto3=True)

    connection = boto3_conn(module, conn_type='client', resource='iam', region=region, endpoint=ec2_url, **aws_connect_params)

    list_iam_users(connection, module)


if __name__ == '__main__':
    main()
