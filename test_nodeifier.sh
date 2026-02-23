#!/bin/bash

# Simple test script for the nodeifier service
# This will send a test payload to the local nodeifier service

PORT=${1:-4312}
URL="http://localhost:$PORT/push"

echo "Testing nodeifier at $URL..."

curl -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "app": "pushbullet",
       "target": "dandroid",
       "title": "TEST ALERT",
       "body": "This is a test message from the local test script to verify nodeifier forwarding."
     }'

echo -e "\n\nTest complete. Check the nodeifier container logs to verify forwarding."
