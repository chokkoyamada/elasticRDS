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

    if cluster_name:
        print data[cluster_name]
    else:
        for cluster in data:
            print cluster

@task
@runs_once
def startup_cluster(cluster_name):
    """RDSクラスターを起動する"""

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
    for replica_config in replica_configs:
        print(cyan("Launching read replica node %s..." %replica_config["id"]))
        try:
            db_info = _get_conn().get_all_dbinstances(replica_config["id"])[0]
            if db_info.status == "available":
                print(cyan("read replica node %s is already launched." %replica_config["id"]))
        except BotoServerError:
            _get_conn().create_dbinstance_read_replica(**replica_config)

        while True:
            db_info = _get_conn().get_all_dbinstances(replica_config["id"])[0]
            if db_info.status == "available":
                break
            print(cyan("waiting for instance to be available... status: %s" %db_info.status))
            sleep(60)

        print(green("read replica node %s is ready." %replica_config["id"]))


