# -*- coding: utf-8 -*-
import boto.rds
from boto.exception import BotoServerError
from fabric.api import task, runs_once
from fabric.colors import *
import json
from time import sleep

@task
@runs_once
def start():
    print(red("hello"))

def _get_conn():
    conn = boto.rds.connect_to_region("ap-northeast-1")
    return conn

@task
@runs_once
def status(cluster_name=None):
    json_data = open("conf/rds_cluster_conf.json")
    data = json.load(json_data)

    print(green(cluster_name))

    db_info = _get_conn().get_all_dbinstances(data[cluster_name]["master_node"]["instance_id"])[0]
    print(magenta("\tmaster"))
    print(cyan("\t\t%s\t%s\t%s" %(db_info.id, db_info.instance_class, db_info.status)))

    print(magenta("\tread replica"))
    for replica_node in data[cluster_name]["replica_nodes"]:
        try:
            db_info = _get_conn().get_all_dbinstances(replica_node["id"])[0]
            print(cyan("\t\t%s\t%s\t%s" %(db_info.id, db_info.instance_class, db_info.status)))
        except BotoServerError:
            pass

@task
@runs_once
def create_cluster(cluster_name, max_replica_num=None):
    """設定ファイルにもとづいてRDSクラスターを起動する"""

    # 設定ファイルを取得
    print(green("Starting up %s..." %cluster_name))
    json_data = open("conf/rds_cluster_conf.json")
    data = json.load(json_data)
    master_config =  data[cluster_name]["master_node"]
    replica_configs = data[cluster_name]["replica_nodes"]

    # マスターインスタンスがあればavailableになるのを待つ、なければスナップショットからリストアして作成
    print(cyan("Launching master node %s..." %master_config["instance_id"]))
    try:
        db_info = _get_conn().get_all_dbinstances(master_config["instance_id"])[0]
        if db_info.status == "available":
            if master_config["instance_class"] != db_info.instance_class:
                _get_conn().modify_dbinstance(
                    id=master_config["instance_id"],
                    instance_class=master_config["instance_class"],
                    apply_immediately=True)
                print(green("master node %s is already launched but changed instance class. Modifying..." %master_config["instance_id"]))
            else:
                print(cyan("master node %s is already launched." %master_config["instance_id"]))
    except BotoServerError:
        _get_conn().restore_dbinstance_from_dbsnapshot(**master_config)

    while True:
        db_info = _get_conn().get_all_dbinstances(master_config["instance_id"])[0]
        if db_info.status == "available":
            break
        print(cyan("waiting for instance to be available... status: %s" %db_info.status))
        sleep(60)

    print(green("master node %s is ready." %master_config["instance_id"]))

    # リードレプリカを作成。一度に1個しか作れないので順に作っていく
    replica_num = 0
    for replica_config in replica_configs:
        replica_num += 1
        # リードレプリカの数が限界値以上の場合
        if (max_replica_num is not None) and (int(replica_num) > int(max_replica_num)):
            try:
                db_info = _get_conn().get_all_dbinstances(replica_config["id"])[0]
                if db_info.status == "available":
                    _get_conn().delete_dbinstance(id=replica_config["id"], skip_final_snapshot=True)
                    print(green("Read replica node num is out of limit. Deleting %s..." %replica_config["id"]))
            except BotoServerError as ex:
                print(cyan("Read replica %s not found." %replica_config["id"]))
        # リードレプリカを作成
        else:
            print(cyan("Launching read replica node %s..." %replica_config["id"]))
            try:
                db_info = _get_conn().get_all_dbinstances(replica_config["id"])[0]
                if db_info.status == "available":
                    if replica_config["instance_class"] != db_info.instance_class:
                        _get_conn().modify_dbinstance(
                            id=replica_config["id"],
                            instance_class=replica_config["instance_class"],
                            apply_immediately=True)
                        print(green("read replica node %s is already launched but changed instance class. Modifying..." %replica_config["id"]))
                    else:
                        print(cyan("read replica node %s is already launched." %replica_config["id"]))
            except BotoServerError:
                _get_conn().create_dbinstance_read_replica(source_id=master_config["instance_id"], **replica_config)

            while True:
                db_info = _get_conn().get_all_dbinstances(replica_config["id"])[0]
                if db_info.status == "available":
                    break
                print(cyan("waiting for instance to be available... status: %s" %db_info.status))
                sleep(60)

            print(green("read replica node %s is ready." %replica_config["id"]))

@task
@runs_once
def modify_instance(instance_id, instance_class):
    _get_conn().modify_dbinstance(
        id=instance_id,
        instance_class=instance_class,
        apply_immediately=True)

