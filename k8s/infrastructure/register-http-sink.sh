#!/bin/bash

# Ensure we port-forward the Kafka Connect service before running this
# kubectl port-forward svc/kafka-connect 8083:8083 &

echo "Registering HTTP Sink connector to send CDC events to resource-sync-worker..."

curl -X POST -H "Content-Type: application/json" --data '{
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
    "retry.backoff.ms": "3000"
  }
}' http://localhost:8083/connectors

echo -e "\nConnector registered!"
