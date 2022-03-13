#!/usr/bin/env python3
#utputs all loggroups with > 1GB of incomingBytes in the past 7 days
#统计输入到cloudwatch log的最多的日志组
import boto3
import sys
from datetime import datetime as dt
from datetime import timedelta

logs_client = boto3.client('logs','us-west-2')
cloudwatch_client = boto3.client('cloudwatch','us-west-2')

def cloudwatch_log_stat(day_delta=7):
    end_date = dt.today().isoformat(timespec='seconds')
    start_date = (dt.today() - timedelta(day_delta)).isoformat(timespec='seconds')
    print("looking from %s to %s" % (start_date, end_date))
    
    paginator = logs_client.get_paginator('describe_log_groups')
    pages = paginator.paginate()
    for page in pages:
         for json_data in page['logGroups']:
            log_group_name = json_data.get("logGroupName") 
    
            cw_response = cloudwatch_client.get_metric_statistics(
               Namespace='AWS/Logs',    
               MetricName='IncomingBytes',
               Dimensions=[
                {
                    'Name': 'LogGroupName',
                    'Value': log_group_name
                },
                ],
                StartTime= start_date,
                EndTime=end_date,
                Period=3600 * 24 * 1,
                Statistics=[
                    'Sum'
                ],
                Unit='Bytes'
            )
            if len(cw_response.get("Datapoints")):
                stats_data = cw_response.get("Datapoints")[0]
                stats_sum = stats_data.get("Sum")   
                sum_GB = stats_sum /  (1000 * 1000 * 1000)
                if sum_GB > 1.0:
                    print("%s = %.2f GB" % (log_group_name , sum_GB))

if __name__ =='__main__':
    day_delta = int(sys.argv[1])
    cloudwatch_log_stat(day_delta)

