#!/bin/bash

# Test the WhatsApp shutdown hoax forward

curl -X 'POST' \
  'http://localhost:8001/api/messages/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "WhatsApp will be off from 11:30 pm to 6:00 am daily. Declared by central govt. Message from Narendra Modi (PM). We have had an over-usage of user names on WhatsApp Messenger. We are requesting all users to forward this message to their entire contact list. If you do not forward this message, we will take it as your account is invalid and it will be deleted within 48 hours.",
  "source": "web_form",
  "metadata": {
    "chat_id": "test-whatsapp",
    "user_id": "test-user-1"
  }
}'
