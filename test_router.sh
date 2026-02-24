#!/bin/bash

# Test script for the new Message Router
# This simulates a frontend submission to the centralized router

PORT=${1:-4300}
URL="http://localhost:$PORT/send-it"

echo "Testing Message Router at $URL..."

curl -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "first_name": "Router",
       "surname": "Tester",
       "number": "0400000000",
       "location": "Test Lab",
       "issue": "General Inquiry",
       "issue_extra": "Testing the fan-out routing capability of the new message-router service.",
       "escooter_make": "Xiaomi",
       "escooter_model": "M365"
     }'

echo -e "\n\nTest complete. Check logs for all 3 services:"
echo "1. message-router: Should show routing to all subprocesses."
echo "2. contact-sync: Should show a new contact received."
echo "3. email-service: Should show an email sent log."
echo "4. nodeifier: Should show a push request received and forwarded."
