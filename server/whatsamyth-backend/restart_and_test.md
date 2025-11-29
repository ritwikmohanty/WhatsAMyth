# Restart and Test Instructions

## 1. Restart your backend server
Stop your current server (Ctrl+C) and restart it:
```bash
uvicorn app.main:app --reload --port 8001
```

## 2. Test with the microchip claim
```bash
curl -X 'POST' \
  'http://localhost:8001/api/messages/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "COVID-19 vaccines contain microchips for tracking people.",
  "source": "web_form",
  "metadata": {
    "chat_id": "demo-test",
    "user_id": "test-user"
  }
}'
```

## Expected Output
You should now see something like:
```json
{
  "message_id": X,
  "is_claim": true,
  "cluster_id": Y,
  "cluster_status": "FALSE",
  "short_reply": "COVID-19 vaccines do not contain microchips or tracking devices.",
  "audio_url": "/media/replies/X.mp3" (or null if TTS fails),
  "needs_verification": false
}
```

## Note about audio_url
If `audio_url` is still `null`, it means TTS (pyttsx3) is failing. This is a separate issue. The fact-checking should work now!
