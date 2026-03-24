#!/bin/bash
set -e

echo "Adding Bitnami Helm repository..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

echo "Installing PostgreSQL with logical replication enabled..."
# This is necessary for Debezium to capture CDC events
helm upgrade --install postgres bitnami/postgresql \
  --set auth.postgresPassword=postgres \
  --set auth.database=appdb \
  --set primary.extendedConfiguration="wal_level=logical" \
  --set architecture=standalone

echo "Installing Kafka (KRaft mode)..."
helm upgrade --install kafka bitnami/kafka \
  --set controller.replicaCount=1 \
  --set broker.replicaCount=1 \
  --set listeners.client.protocol=PLAINTEXT \
  --set autoCreateTopicsEnable=true

echo "Infrastructure deployed successfully!"
echo "Note: Wait for pods to become ready before deploying Kafka Connect."
