import os
import json
import time
from confluent_kafka import Consumer, KafkaError
from kubernetes import client, config
from kubernetes.client.rest import ApiException

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "dbserver1.public.app_configs")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "k8s-sync-worker-group")
CRD_GROUP = "poc.gitrenderer.com"
CRD_VERSION = "v1alpha1"
CRD_PLURAL = "appconfigs"
NAMESPACE = os.getenv("NAMESPACE", "default")

def init_k8s_client():
    try:
        config.load_incluster_config()
        print("Loaded within-cluster config.")
    except config.ConfigException:
        print("Loaded local kubeconfig.")
        config.load_kube_config()
    
    return client.CustomObjectsApi()

def process_cdc_event(api_instance, message_value):
    if not message_value:
        return
        
    payload = message_value.get("payload")
    if not payload:
        return
        
    op = payload.get("op")
    if not op:
        return
        
    # 'c' for create, 'r' for read (initial snapshot), 'u' for update, 'd' for delete
    if op in ("c", "r", "u"):
        after = payload.get("after")
        if not after:
            return
        apply_custom_resource(api_instance, after)
    elif op == "d":
        before = payload.get("before")
        if not before:
            return
        delete_custom_resource(api_instance, before.get("name"))

def apply_custom_resource(api_instance, data):
    name = data.get("name")
    
    # K8s resource names must be valid DNS subdomains
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    
    cr = {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "AppConfig",
        "metadata": {
            "name": k8s_name,
            "namespace": NAMESPACE
        },
        "spec": {
            "id": data.get("id"),
            "name": name,
            "repository_url": data.get("repository_url"),
            "branch": data.get("branch"),
            "environment": data.get("environment")
        }
    }
    
    try:
        # Check if exists
        api_instance.get_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name
        )
        # Update if exists
        cr["metadata"]["resourceVersion"] = "" # Allow patch
        api_instance.patch_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name,
            body=cr
        )
        print(f"Updated CR: {k8s_name}")
    except ApiException as e:
        if e.status == 404:
            # Create
            api_instance.create_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=NAMESPACE,
                plural=CRD_PLURAL,
                body=cr
            )
            print(f"Created CR: {k8s_name}")
        else:
            print(f"Error checking/updating CR: {e}")

def delete_custom_resource(api_instance, name):
    k8s_name = str(name).lower().replace("_", "-").replace(" ", "-")
    
    try:
        api_instance.delete_namespaced_custom_object(
            group=CRD_GROUP,
            version=CRD_VERSION,
            namespace=NAMESPACE,
            plural=CRD_PLURAL,
            name=k8s_name
        )
        print(f"Deleted CR: {k8s_name}")
    except ApiException as e:
        if e.status == 404:
            print(f"CR already deleted: {k8s_name}")
        else:
            print(f"Error deleting CR: {e}")

def main():
    api_instance = init_k8s_client()
    
    # Wait a bit for kafka to be ready
    time.sleep(10)
    
    conf = {
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': KAFKA_GROUP_ID,
        'auto.offset.reset': 'earliest'
    }
    
    consumer = Consumer(conf)
    consumer.subscribe([KAFKA_TOPIC])
    
    print(f"Subscribed to topic {KAFKA_TOPIC}. Polling...")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break
            
            val = msg.value()
            if val:
                try:
                    event = json.loads(val.decode('utf-8'))
                    process_cdc_event(api_instance, event)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

if __name__ == '__main__':
    main()
