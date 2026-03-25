#!/bin/bash

echo "Registering HTTP Sink connector from within the cluster..."

kubectl exec deployment/kafka-connect -- curl -s -X POST -H "Content-Type: application/json" --data '{
  "name": "resource-sync-http-sink",
  "config": {
    "connector.class": "io.aiven.kafka.connect.http.HttpSinkConnector",
    "tasks.max": "1",
    "topics": "dbserver1.public.app_configs",
    "http.url": "http://resource-sync-worker:8000/sync",
    "http.authorization.type": "none",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": "false",
    "max.retries": "1000",
    "retry.backoff.ms": "3000",
    "transforms": "dropTombstones",
    "transforms.dropTombstones.type": "org.apache.kafka.connect.transforms.Filter",
    "transforms.dropTombstones.predicate": "isTombstone",
    "predicates": "isTombstone",
    "predicates.isTombstone.type": "org.apache.kafka.connect.transforms.predicates.RecordIsTombstone"
  }
}' http://localhost:8083/connectors

echo -e "\nConnector registered!"
