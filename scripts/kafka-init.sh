#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="gridpulse-kafka"
BOOTSTRAP_SERVER="localhost:9092"

TOPICS=(
  "gridpulse.eia.region-data.v1"
  "gridpulse.nws.forecast.v1"
  "gridpulse.afdc.ev-stations.v1"
  "gridpulse.dead-letter.v1"
)

echo "Waiting for GridPulse Kafka..."

for attempt in {1..30}; do
  if docker exec "${CONTAINER_NAME}" \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --list >/dev/null 2>&1
  then
    echo "Kafka is ready."
    break
  fi

  if [ "${attempt}" -eq 30 ]; then
    echo "Kafka did not become ready in time."
    exit 1
  fi

  sleep 2
done

echo
echo "Creating GridPulse topics..."

for topic in "${TOPICS[@]}"; do
  docker exec "${CONTAINER_NAME}" \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions 3 \
    --replication-factor 1
done

echo
echo "GridPulse Kafka topics:"
echo

docker exec "${CONTAINER_NAME}" \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "${BOOTSTRAP_SERVER}" \
  --list

echo
echo "Kafka initialization completed."
