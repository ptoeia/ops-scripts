#!/usr/bin/env python
#coding=utf-8
#create rocketmq topic on alicloud

import time
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential
from aliyunsdkcore.auth.credentials import StsTokenCredential

request = CommonRequest()

credentials = AccessKeyCredential(
    'xxx'
    'xxx'
)

client = AcsClient(
    region_id='mq-internet-access', 
    credential=credentials
)

def create_topic(
    topic_name: str,
    remark:str,
    message_type: str='0',
    instance_id:str='MQ_INST_1708083130941856_BX1LUdXV'
):
    request.set_accept_format('json')
    request.set_domain('ons.mq-internet-access.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('http') # https | http
    request.set_version('2019-02-14')
    request.set_action_name('OnsTopicCreate')
    
    request.add_query_param('Topic', topic_name)
    request.add_query_param('MessageType', message_type)
    request.add_query_param('InstanceId', instance_id)
    request.add_query_param('Remark', remark)
    
    try:
        response = client.do_action(request)
        print(str(response, encoding = 'utf-8'))
        print(f'create topic "{topic_name}" successed!')
    except Exception as e:
        print(e)
        print(f'create topic "{topic_name}" failed!')

topic_list = [
    ('PAY_TRANSFER_FAIL_RETRY_TOPIC','商家分账失败重新分账TOPIC','5'),
    ('ORDER_LIFECYCLE_TOPIC','订单生命周期变动通知','1'),
    ('STORE_USERS_BIND_TOPIC','存量用户绑定/解绑通知','0'),
    ('MINI_PAY_TRANSFER_SETTLE_TOPIC','小程序支付分账-结算TOPIC','0'),
    ('USERS_AFTER_SALE_MESSAGE_TOPIC','售后消息通知','0'),
    ('DINGDING_MESSAGE_TOPIC','发送钉钉消息','0'),
]

for topic in topic_list:
    print(f'start to create topic: {topic[0]}')
    create_topic(topic[0], topic[1],topic[2])
    time.sleep(1)

