elasticRDS
==========

auto-scaling like feature in RDS using python and boto

# Requirements:
```
python(>2.7)
fabric(>1.4.3)
boto(>2.9.2)
```

/etc/boto.cfg
```
[Credentials]
aws_access_key_id = <YOUR ACCESS KEY>
aws_secret_access_key = <YOUR SECRET KEY>
```

# Cluster Configuration

conf/rds_cluster_conf.json
```javascript
{
    "cluster1": {                                    //cluster name(only used in the script)
        "master_node": {
            "identifier": "qiitabase201305111613",   //name of db snapshot
            "instance_id": "cluster1m01",
            "instance_class": "db.t1.micro",
            "multi_az": true,
            "db_subnet_group_name" : "qiita"         //(optional) if you'd like to create in VPC
        },
        "replica_nodes": [
            {
                "id": "cluster1s01",
                "instance_class": "db.t1.micro"
            },
            {
                "id": "cluster1s02",
                "instance_class": "db.t1.micro"
            }
        ]
    }
}
```

# Basic Usage:

### creates a RDS cluster based on conf/rds_cluster_conf.json
```
fab create_cluster:<cluster_name>
```

### creates a RDS cluster, and limits number of read replica
```
fab create_cluster:<cluster_name>,max_replica_num=1
```

Read replica will be created by cluster configuration.
but when you specify max_replica_num:
* Read replica will be created no greater than "max_replica_num".
* If there are 3 replica in config and "max_replica_num=2", only 2 replica will be created. If there are already 3 replicas launched, the last one will be deleted.
* If there are 3 replica in config and "max_replica_num=4", only 3 replica will be created.

## Modify instance class

```
fab modify_instance:cluster1m01,db.m1.large
```

will just upgrade instance class, it will work on both master and read replica.
Just make sure that master db is multi-az configured or multiple read replica exists since the instance will not work during upgrade.

## Display current cluster info

```
$ fab status:cluster2
cluster2
    master
          cluster2m01     db.t1.micro     available
     read replica
          cluster2s01     db.t1.micro     available
```

## Use with crontab

* sample crontab

```
0 1 * * * /usr/local/bin/fab create_cluster:cluster1,max_replica_num=1
0 1 * * * /usr/local/bin/fab modify_instance:cluster1m01,db.t1.micro

0 8 * * * /usr/local/bin/fab create_cluster:cluster1,max_replica_num=3
0 8 * * * /usr/local/bin/fab modify_instance:cluster1m01,db.m1.small

0 17 * * * /usr/local/bin/fab create_cluster:cluster1,max_replica_num=4
0 17 * * * /usr/local/bin/fab modify_instance:cluster1m01,db.m1.large
```

If would be great if you'd like to upgrade instance during daytime and downgrade during nighttime.

## Use with HAProxy for load balancing read replica

/etc/haproxy/haproxy.cfg

```
global
    log         127.0.0.1 local2
    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     4000
    user        haproxy
    group       haproxy
    daemon
    stats socket /var/lib/haproxy/stats

defaults
    mode                    tcp
    log                     global
    retries                 3
    timeout connect         10s
    timeout client          1m
    timeout server          1m

listen mysql
    bind    0.0.0.0:3306
    mode    tcp
    option  mysql-check
    balance leastconn
    server  slave1 cluster1s01.xxxxx.ap-northeast-1.rds.amazonaws.com:3306 check port 3306 inter 10000 fall 2
    server  slave2 cluster1s02.xxxxx.ap-northeast-1.rds.amazonaws.com:3306 check port 3306 inter 10000 fall 2
    server  slave3 cluster1s03.xxxxx.ap-northeast-1.rds.amazonaws.com:3306 check port 3306 inter 10000 fall 2
    server  master cluster1m01.xxxxx.ap-northeast-1.rds.amazonaws.com:3306 check port 3306 backup
```
(reference: http://blog.cloudpack.jp/2011/11/server-news-haproxy14-mysql-failover.html)
