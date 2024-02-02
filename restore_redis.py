import json
import boto3
import sys
import threading
import time
import sys
import queue
import logging
from datetime import datetime,timedelta
from dateutil.tz import *
# restore redis cluster from sanpshot

client = boto3.client('elasticache','us-west-2')

def is_exist(rgid):
    """验证rdis实例是否存在
    :param instance_id: redis复制组id
    """
    try:
        response = client.describe_replication_groups(
            ReplicationGroupId = rgid
        )
        return True
    except client.exceptions.ReplicationGroupNotFoundFault as e:
        print(f'redis instance "{rgid}" does not exist')
        return

def generate_cacheid(rgid):
    """生成cacheid"""
    CacheId='test{}{}{}'.format(
         str(rgid)[0:5],
         str(rgid)[-5:],
         datetime.now().strftime('%m%d')
     )
    return CacheId

class Producer(threading.Thread):
    def __init__(self, source_clusterid_queue, target_clusterid_queue):
        threading.Thread.__init__(self)
        self.source_clusterid_queue = source_clusterid_queue
        self.target_clusterid_queue = target_clusterid_queue

    def run(self):
        source_clusterid = self.source_clusterid_queue.get()
        self.restore_cache(source_clusterid)
        print(f"restored {source_clusterid} finished!")
        #target_clusterid = generate_cacheid(source_clusterid)
        self.target_clusterid_queue.put(source_clusterid)
        self.source_clusterid_queue.task_done()

    def _get_cache_type(self,clusterid):
        """
         获取redis实例类型
        :params clusterid redis集群名称
        """
        response = client.describe_replication_groups(
            ReplicationGroupId = clusterid
         )
        cache_type  = response['ReplicationGroups'][0]['CacheNodeType']
        node_id  = response['ReplicationGroups'][0]['MemberClusters'][0]
        return node_id,cache_type

    def _get_cache_version(self,rgid):
        """
         获取redis版本
        """
        cacheid,_ = self._get_cache_type(rgid)
        response = client.describe_cache_clusters(
            CacheClusterId=cacheid,
        )
        engine = response['CacheClusters'][0]['Engine']
        version = '.'.join(response['CacheClusters'][0]['EngineVersion'].split('.')[0:2])
        return f'{engine}{version}'

    def create_cahce_paramenter_group(self,rgid,env='test'):
        """创建参数组"""
        version = self._get_cache_version(rgid)
        target_cache_paramter_group=f'{env}-{rgid}'
        try:
            response = client.create_cache_parameter_group(
                CacheParameterGroupName=target_cache_paramter_group,
                CacheParameterGroupFamily=version,
                Description=target_cache_paramter_group
            )
            return response['CacheParameterGroup']['CacheParameterGroupName']
        except client.exceptions.CacheParameterGroupAlreadyExistsFault as e:
            return target_cache_paramter_group

    def _get_latest_snapshot(self,clusterid):
        """
         获取最新的redis快照
        """
        response = client.describe_replication_groups(
            ReplicationGroupId = clusterid
         )
        redis_node_list = response['ReplicationGroups'][0]['MemberClusters']
        if not redis_node_list:
            print('no redis exist')
            raise Exception('no redis exist')

        snapshot_list = []
        for each in redis_node_list:
            response = client.describe_snapshots(CacheClusterId=each)
            for each in response['Snapshots']:
                if each['SnapshotStatus'] == 'available':
                    snapshot_list.append(
                       {
                           'SnapshotName': each['SnapshotName'],
                           'CacheSize':    each['NodeSnapshots'] [0]['CacheSize'],
                           'CreateTime':   each['NodeSnapshots'][0]['SnapshotCreateTime']
                       }
                     )
        if not snapshot_list:
            print('no snapshot exist')
            raise Exception('no snapshot exist')
            sys.exit()
        snapshot_list.sort(key = lambda x:x['CreateTime'])
        snapshot = snapshot_list[0]
        return snapshot

    def restore_cache(self,clusterid):
        """ 恢复快照"""
        snapshot = self._get_latest_snapshot(clusterid)
        cache_type = self._get_cache_type(clusterid)
        target_clusterid = generate_cacheid(clusterid)
        ParameterGroupName = self.create_cahce_paramenter_group(clusterid)
        print(f'start createing redis {target_clusterid}')
        response = client.create_replication_group(
            ReplicationGroupId=target_clusterid,
            ReplicationGroupDescription = target_clusterid,
            #CacheNodeType=cache_type,
            NotificationTopicArn='',
            CacheParameterGroupName=ParameterGroupName,
            Engine='redis',
            CacheSubnetGroupName='test-env-subnet',
            SnapshotName = snapshot['SnapshotName'],
            SnapshotRetentionLimit = 0,
            Tags = [
                {
                  'Key': 'Env',
                  'Value': 'test'
                },
           ],
        )
        ReplicationGroupId = response['ReplicationGroup']['ReplicationGroupId']
        redis_create_waiter = client.get_waiter('replication_group_available')
        redis_create_waiter.wait(
            ReplicationGroupId = ReplicationGroupId,
            WaiterConfig = {
                             'Delay': 30,
                             'MaxAttempts': 30
                           }
        )

class Consumer(threading.Thread):
    def __init__(self, target_clusterid_queue):
        threading.Thread.__init__(self)
        self.clusterid_queue = target_clusterid_queue

    def _dns_update(self,cluster_id,domain='.clubfactory.test.',
            address_suffix='mxcyd8.0001.usw2.cache.amazonaws.com'):
        # 更新dns
        if cluster_id == '_finish':
            pass  #忽略结束信号
        target_clusterid = generate_cacheid(cluster_id)
        client = boto3.client('route53')
        response = client.change_resource_record_sets(
            HostedZoneId = 'Z2JNFNBSAKYRGJ',
            ChangeBatch = {
                'Comment': 'string',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': cluster_id+domain,
                            'Type': 'CNAME',
                            'TTL': 123,
                            'ResourceRecords': [
                                {
                                    'Value': f'{target_clusterid}.{address_suffix}'
                                },
                            ],
                        }
                    },
                ]
            }
        )
        waiter = client.get_waiter('resource_record_sets_changed')
        waiter.wait(Id=response['ChangeInfo']['Id'])

    def run(self):
        while True:
            print("start consumer")
            ClusterId = self.clusterid_queue.get()
            self._dns_update(ClusterId)
            print(f"{ClusterId} update done")
            self.clusterid_queue.task_done()
            if ClusterId == '_finish':
                break

def delete_expired_cache(origin_clusterid):
    """ 删除七天前生成的redis实例 """
    expired_cacheId='test{}{}{}'.format(
        str(origin_clusterid)[0:5],
        str(origin_clusterid)[-5:],
        (datetime.now()+timedelta(-7)).strftime('%m%d')
    )
    try:
        response = client.delete_replication_group(
            ReplicationGroupId = expired_cacheId,
            RetainPrimaryCluster=False,
        )
        print(f"delete redis:{expired_cacheId}")
        return response
    except Exception as e:
        print(f"expired cache {expired_cacheId} doesn't exist")

def validate(redis_list):
    clusterid_list =[
        redis
        for redis in redis_list
        if is_exist(redis)
    ]
    assert clusterid_list,sys.exit()
    return clusterid_list

if __name__=='__main__':
    clusterid_list = validate(['strategy-data'])

    source_clusterid_queue = queue.Queue()
    target_clusterid_queue = queue.Queue()

    restore_th_list=[]
    #启动生产者和消费者线程
    for x in clusterid_list:
        dns_update_th = Consumer(target_clusterid_queue)
        dns_update_th.start()
        restore_th = Producer(source_clusterid_queue,target_clusterid_queue)
        restore_th_list.append(restore_th)
        restore_th.start()

    for clusterid in clusterid_list:
        source_clusterid_queue.put(clusterid)

    #阻塞生产者队列，等待线程完成
    #for th in restore_th_list:
    #    threading.Thread.join(th)
    source_clusterid_queue.join()

    #向queue发送结束结束信号，解除消费者队列阻塞
    for clusterid in clusterid_list:
        target_clusterid_queue.put('_finish')

    target_clusterid_queue.join()
    print('All restore work done')

   # for clusterid in clusterid_list:
   #     delete_expired_cache(clusterid)
