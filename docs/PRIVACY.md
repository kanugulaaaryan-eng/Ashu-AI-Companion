# Ashu v0.4 — privacy & security

Privacy is an architectural property here, not a screen added at the end.

## Local-first

- Memory, personality state and the activity log are stored in a local SQLite
  database and a JSON sidecar on the device. There is no telemetry and no
  analytics layer.
- The local model, when present, runs on the device. Cloud fallback is **off by
  default**.

## Permissions

- Permissions are requested **individually**, each with a plain-language
  explanation (`PhonePermissions.CATALOG` / onboarding step 7), never as one
  blanket prompt.
- `MANAGE_EXTERNAL_STORAGE`, notification-listener access and usage-access are
  optional and off unless the user enables them in Android settings.
- File tools operate inside an Ashu-managed sandbox unless the user explicitly
  grants broad access.
- Permissions can be revoked at any time in Android settings; Ashu re-reports
  her real capabilities.

## Confirmations for risky actions

- `tools/confirmations.py` defines the destructive set (write/edit/delete file,
  system reminder, open app, music control, camera).
- Ashu never performs these silently: she shows the exact action
  (`describe_action`) and waits for **Confirm** or **Cancel**. The decision is
  logged locally.
- The model cannot create a pending action. Only the decision engine can, and
  every action still passes permission + confirmation checks.

## Untrusted model output

- `security/privacy.py::sanitize_model_output` treats every model reply
  (local or cloud) as untrusted text: it strips control characters, caps
  length, and neutralises lines that impersonate a system/developer/assistant
  turn or try to trigger a tool.
- Model output can therefore never bypass permission checks, change settings,
  or invoke a tool. Tests in `tests/test_v0_4_permissions_confirmations.py`
  assert this.

## Memory

- Automatic memory extraction refuses secrets (`is_sensitive`: passwords,
  OTPs, PINs, API/secret keys, tokens).
- Every memory records provenance (`session_id`, `source_message`,
  `memory_type`) and can be reviewed, edited, pinned or deleted.
- Conversational commands work: "what do you remember about me?",
  "remember that…", "forget what I just told you", "delete everything you know
  about me" (which asks for confirmation first).

## Cloud fallback

- Disabled by default; enabling it is an explicit user choice.
- The key is read from an environment variable / device keystore — never
  hardcoded and never logged, and never exposed in capability reports.
- Replies routed to the cloud are labelled in the UI (`origin=cloud` +
  `model_notice`).
- Memories/files are not included in a cloud request unless
  `cloud_include_memories` is separately enabled.

## Data control

- `DataExporter` produces a plain snapshot of everything Ashu stored.
- `wipe_all()` deletes profile, preferences, goals, projects, people, memories,
  summaries and the activity log.
- The privacy screen exposes export, revoke and delete-everything.
