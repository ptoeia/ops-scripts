#!/usr/bin/env python3

import json
import boto3
import re
from functools import wraps
from datetime import datetime

#Author:gewuzhang
#Purpose: aws ec2|rds官方维护通知接入中间件企业微信报警，在 aws lambda中使用

TOPICARN = 'arn:aws:sns:us-west-2:660338696248:CloudWatchAlarm'
DATE_NOW=datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')[:-3]+"+0000"

#中间件企业微信消息接入格式
ALARM_MSG={
    "AlarmName": "AWS EC2/RDS 官方维护预告",
    "AWSAccountId": "660338696248",
    "NewStateValue": "ALARM",
    "NewStateReason": "",
    "StateChangeTime": DATE_NOW, 
    "Region": "US West (Oregon)",
    "OldStateValue": "OK",
    "Trigger": {
        "MetricName": "aws ec2 maintenance",
        "Namespace": "AWS/Maintenance",
        "StatisticType": "Statistic",
        "Statistic": "",
        "Unit": "",
        "Dimensions": [
            {
                "value": "",
                "name": "InstanceId"
            }
        ],
        "Period": "",
        "EvaluationPeriods": "",
        "ComparisonOperator": "",
        "Threshold": "",
        "TreatMissingData": "",
        "EvaluateLowSampleCountPercentile": ""
    }
}

def send_to_sns(msg):
    sns_client = boto3.client('sns')
    try:
        sns_response = sns_client.publish(
        TopicArn = TOPICARN,
        Message = msg,
        Subject = 'aws maintenance notice'
        )
        return('Publish to SNS Channel Message Id:{}'.format(sns_response['MessageId']))
    except Exception as e:
        return(str(e))

def alarm_send(func):
    @wraps(func)
    def _wrapper():
        msg_list = func()
        if msg_list:
            for msg in msg_list:
                send_to_sns(msg)
    return _wrapper

@alarm_send
def get_ec2_maintenance_notices():
    client=boto3.client('ec2','us-west-2')
    response=client.describe_instance_status(
        Filters=[
           {
                'Name': 'event.code',
                'Values': [
                    'instance-reboot',
                    'system-reboot', 
                    'system-maintenance',
                    'instance-retirement',
                    'instance-stop'
                ]
            },
        ],
    )['InstanceStatuses']
    if response:
        alarm_msg_list = []
        for each in response:
            # 去除已维护完成的通知
            if re.search('Completed',each['Events'][0]['Description']):
                continue
            else:
                ALARM_MSG["AlarmDescription"] = each['InstanceId']+" will under maintenance"
                ALARM_MSG["NewStateReason"] = each['Events'][0]['Description']
                ALARM_MSG["Trigger"]["Dimensions"][0]['value'] = each['InstanceId']
                alarm_msg_list.append(json.dumps(ALARM_MSG))
        return alarm_msg_list

@alarm_send
def get_rds_maintenance_notices():
    client = boto3.client('rds','us-west-2')
    response = client.describe_pending_maintenance_actions()['PendingMaintenanceActions']
    if response:
        alarm_msg_list = []
        for each in response:
            if re.search('maintenance',each['PendingMaintenanceActionDetails'][0]['Action']):
                ALARM_MSG["AlarmName"] = "AWS RDS 维护通知"
                ALARM_MSG["AlarmDescription"] = each['ResourceIdentifier']+" will under maintenance"
                ALARM_MSG["NewStateReason"]= each['PendingMaintenanceActionDetails'][0]['Description']
                ALARM_MSG["Trigger"]["Dimensions"][0]['value']=each['ResourceIdentifier']
                alarm_msg_list.append(json.dumps(ALARM_MSG)) 
        return alarm_msg_list
    else:
        raise Exception('no msg')

def lambda_handler(event, context):
    """ lambda 入口函数 """
    get_ec2_maintenance_notices()
    get_rds_maintenance_notices()