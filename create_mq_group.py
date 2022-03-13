#!/usr/bin/env python
#coding=utf-8
# create rocketmq group on alicloud

import json
import time
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkcore.auth.credentials import StsTokenCredential

credentials = AccessKeyCredential(
    'xxxxx', 
    'xxxxx'
)

client = AcsClient(
    region_id='mq-internet-access', 
    credential=credentials
)

request = CommonRequest()

def create_group(instance_id:str,group_id:str,remark:str='group'):
    """
    param instance_id: rocketmq 实例id
    param group_id: rocketmq group id
    param remark: group 备注
    """
    request.set_accept_format('json')
    request.set_domain('ons.mq-internet-access.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('http') # https | http
    request.set_version('2019-02-14')
    request.set_action_name('OnsGroupCreate')
    
    request.add_query_param('GroupId', group_id)
    request.add_query_param('Remark', remark)
    request.add_query_param('InstanceId', instance_id)
    
    response = client.do_action(request)
    # python2:  print(response) 
    print(str(response, encoding = 'utf-8'))

def get_group_by_instance(instance_id:str='MQ_INST_1708083130941856_BXtRmR97'):
    """
    param instance_id: rocketmq 实例id
    """
    request.set_accept_format('json')
    request.set_domain('ons.mq-internet-access.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('http') # https | http
    request.set_version('2019-02-14')
    request.set_action_name('OnsGroupList')
    
    request.add_query_param('InstanceId',instance_id)
    
    try:
        response = json.loads(client.do_action(request))
        group_list = response["Data"]["SubscribeInfoDo"]
        for group in group_list:
            yield group
    except Exception as e:
        print(e)
        print('get mq group list failed')

for group in get_group_by_instance():
    print('start to create group: '+ group['GroupId'])
    create_group('MQ_INST_1708083130941856_BX1LUdXV',group['GroupId'],group['Remark'])
    time.sleep(2)
