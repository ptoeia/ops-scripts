#!/usr/bin/env python3
#批量调整aws线上db存储最大自动扩容阈值

import boto3
import time

client = boto3.client('rds','us-west-2')

def get_rds_list():
    response = client.describe_db_instances(
    )
    assert response['DBInstances'], 'rds not exist'
    for each in response['DBInstances']:
        if not each['DBInstanceIdentifier'].startswith(('perf','test','pre')):
           yield each['DBInstanceIdentifier']

def UpgradeMaxAllocateStorage(storage=2048):
    """ 调整rds自动扩容功能的最大存储阈值
    :param sotrage: 存储容量GB  
    """
    for rds in get_rds_list():
        print(f"start to change rds--{rds}")
        time.sleep(3)
        try:
            response = client.modify_db_instance(
                DBInstanceIdentifier=rds,
                #ApplyImmediately=True,
                MaxAllocatedStorage=storage
            )
        except Exception as e:
           print(str(e)+rds)

if __name__ =='__main__':
    UpgradeMaxAllocateStorage()