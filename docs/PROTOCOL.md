# Local protocol v2

Android and the Python agent communicate through a small versioned JSON-over-HTTP interface during development.

## GET

- `/v1/health`
- `/v1/profile`
- `/v1/memory`

## POST

- `/v1/setup`
- `/v1/chat`

`/v1/chat` returns:

```json
{
  "text": "...",
  "session_id": "...",
  "action_type": "answer",
  "suggestions": [],
  "followup_question": "",
  "mood": "calm",
  "relationship_stage": "best_friend",
  "protocol_version": "2"
}
```

The Android layer uses `mood` and `relationship_stage` to drive the character presentation without embedding personality logic into the UI.
