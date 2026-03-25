#!/bin/bash

echo "Registering Postgres Debezium connector from within the cluster..."

kubectl exec deployment/kafka-connect -- curl -s -X POST -H "Content-Type: application/json" --data '{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "postgres-postgresql",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "appdb",
    "topic.prefix": "dbserver1",
    "plugin.name": "pgoutput",
    "tombstones.on.delete": "false"
  }
}' http://localhost:8083/connectors

echo -e "\nConnector registered!"
