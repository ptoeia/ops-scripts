#!/usr/bin/env python
import boto3
from concurrent.futures import ThreadPoolExecutor,as_completed
#从快照创建压测RDS

arn_prefix = "arn:aws:rds:us-west-2:660338696248:db"
client = boto3.client('rds', 'us-west-2')

def exist(instance_id):
    """验证rds实例是否存在
    :param instance_id: rds实例id
    """
    try:
        response = client.describe_db_instances(
            DBInstanceIdentifier=instance_id
        )
        return True
    except client.exceptions.DBInstanceNotFoundFault as e:
        print(f'rds instance "{instance_id}" does not exist')
        return

def update_tag(instance_id):
    """更改标签"""
    response = client.add_tags_to_resource(
        ResourceName=f'{arn_prefix}:{instance_id}',
        Tags=[
            {
                'Key': 'Env',
                'Value': 'perf'
            },
        ]
    )
    return

def db_create_waiter(instance_id):
    """ 等待创建阻塞器"""
    db_create_waiter = client.get_waiter('db_instance_available')
    db_create_waiter.wait(
        DBInstanceIdentifier=instance_id,
    )
    return

def get_latest_snapshot(instance_id):
    """获取最新快照"""
    response = client.describe_db_snapshots(
        DBInstanceIdentifier=instance_id,
    )
    snapshots = response['DBSnapshots']
    if not snapshots:
        raise Exception("Error,the instance have no snapshot exist")
    snapshot_list = []
    for each in snapshots:
        if each['Status'] == 'available':
            snapshot_list.append(
                {
                    'DBSnapshotArn':each['DBSnapshotArn'],
                    'DBSnapshotId': each['DBSnapshotIdentifier'],
                    'CreateTime':   each['SnapshotCreateTime']
                }
            )
    snapshot_list.sort(key = lambda x:x['CreateTime'])
    snapshot = snapshot_list[-1]
    return snapshot['DBSnapshotArn']

def get_db_detail(instance_id):
    """获取db详情"""
    response = client.describe_db_instances(
        DBInstanceIdentifier = instance_id
    )
    parameter_group_name = response['DBInstances'][0]['DBParameterGroups'][0]['DBParameterGroupName']
    engine = response['DBInstances'][0]['Engine']
    return engine, parameter_group_name
    
def create_parameter_group(source_parameter_group_name):
    """创建实例参数组"""
    target_db_parameter_group_name = f'perf-{source_parameter_group_name}'
    try:
        response = client.copy_db_parameter_group(
            SourceDBParameterGroupIdentifier=source_parameter_group_name,
            TargetDBParameterGroupIdentifier=target_db_parameter_group_name,
            TargetDBParameterGroupDescription=target_db_parameter_group_name
        )
        print(f"use parameter group {target_db_parameter_group_name}")
        return response['DBParameterGroup']['DBParameterGroupName']
    except client.exceptions.DBParameterGroupAlreadyExistsFault as e:
        print(f"use already exist parameter group {target_db_parameter_group_name}")
        return f'{target_db_parameter_group_name}'

def restore_db_from_snapshot(instance_id, engine, snapshot_id, parameter_group):
    """从快照生成实例"""
    target_instance_id = f'perf-{instance_id}'
    response = client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=target_instance_id,
        DBSnapshotIdentifier=snapshot_id,
        Engine=engine,
        #EngineVersion='string',
        DBSubnetGroupName='perf-subnet',
        #VpcSecurityGroupIds=[
        #    'string',
        #],
        #EngineMode='string',
        DBParameterGroupName=parameter_group,
        CopyTagsToSnapshot=True
    )
    print(f"start to create db '{target_instance_id}' with snapshot....")
    target_instance_id=response['DBInstance']['DBInstanceIdentifier']
    db_create_waiter(target_instance_id)
    update_tag(target_instance_id)
    return f'RDS instance "{target_instance_id}" created success!'

def do_restore(arg):
    """ 封装原始函数，容纳多个参数"""
    instance_id, engine, snapshot_id, parameter_group_name = arg
    return restore_db_from_snapshot(instance_id, engine, snapshot_id, parameter_group_name)

def generate_run_parameters(instance_id_list):
    """ 生成参数"""
    instance_id_list = [instance_id for instance_id in instance_id_list if exist(instance_id)]
    if not instance_id_list:
        raise Exception('there is no rds exist')
    for instance_id in instance_id_list:
        snapshot_id = get_latest_snapshot(instance_id)
        engine, source_parameter_group_name = get_db_detail(instance_id)
        parameter_group_name = create_parameter_group(source_parameter_group_name)
        run_parameters = (instance_id, engine, snapshot_id, parameter_group_name)
        yield run_parameters

def creaat_db_account():
    """创建管理账户"""
    pass

def main(instance_id_list):
    with ThreadPoolExecutor() as executor:
        task_list = []
        for parameter in generate_run_parameters(instance_id_list):
            obj = executor.submit(do_restore, parameter)
            task_list.append(obj)

    for future in as_completed(task_list):
        data = future.result()
        print(data)

if __name__=='__main__':
    instance_id_list = ['app-static','friday']
    main(instance_id_list)
