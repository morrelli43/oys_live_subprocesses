#!/bin/bash

# Simple test script for the message-center service
# This will send a test payload to the local message-center service

PORT=${1:-3003}
URL="http://localhost:$PORT/push"

echo "Testing message-center at $URL..."

curl -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "app": "test-script",
       "target": "dandroid",
       "title": "TEST ALERT",
       "body": "This is a test message from the local test script to verify message-center forwarding."
     }'

echo -e "\n\nTest complete. Check the message-center container logs to verify forwarding."
