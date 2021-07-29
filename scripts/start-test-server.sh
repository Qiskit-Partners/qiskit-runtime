#!/bin/bash

NUM_WORKERS=${NUM_WORKERS:-1}
for (( i=1; i<=NUM_WORKERS; i++ )); do
    echo "Starting worker #$i"
    python3 qiskit_runtime/test_server/worker.py &
done

echo "Starting Redis"
echo never > /sys/kernel/mm/transparent_hugepage/enabled
redis-server &

echo "Starting server"
uvicorn --host 0.0.0.0 --port 8000 qiskit_runtime.test_server:runtime --reload --reload-dir qiskit_runtime