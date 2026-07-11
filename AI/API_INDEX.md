# API Index

## FastAPI Surface

Source: `api/main.py`

Known endpoints:

- `GET /health`
- `GET /api/status`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/community/invite`
- `POST /api/community/invite/accept`
- `GET /api/community/members`
- `POST /api/community/members/{username}/role`
- `GET /api/community/feed`
- `GET /api/community/invites`
- `GET /api/release-evidence`
- `POST /api/chat`
- `POST /v1/chat/completions`
- `GET /api/safety/metrics`
- `GET /api/safety/telemetry`
- `GET /api/safety/status`

## Request Models

- `Message`
- `ChatRequest`
- `OpenAIChatRequest`
- `RegisterRequest`
- `LoginRequest`
- `InviteRequest`
- `AcceptInviteRequest`
- `RoleUpdateRequest`

## Important Environment Variables

- `CTOA_ENV`
- `CTOA_LOCAL_MODEL_URL`
- `CTOA_LOCAL_MODEL_NAME`
- `CTOA_MODEL_SMALL`
- `CTOA_MODEL_LARGE`
- `CTOA_SMALL_MODEL_URL`
- `CTOA_LARGE_MODEL_URL`
- `CTOA_SMALL_API_KEY`
- `CTOA_LARGE_API_KEY`
- `CTOA_ROUTE_DEFAULT`
- `CTOA_ROUTER_LONG_CHARS`
- `CTOA_ROUTER_LONG_TURNS`
- `CTOA_QUALITY_RETRY`
- `CTOA_ROUTER_LOG`
- `CTOA_RELEASE_EVIDENCE_FILE`
- `CTOA_AUTH_STORE_FILE`
- `CTOA_AUTH_REQUIRED`
- `CTOA_API_SELF_REGISTER_ENABLED`
- `CTOA_API_SELF_REGISTER_CODE`
- `CTOA_JWT_SECRET`
- `CTOA_JWT_TTL_SECONDS`
- `CTOA_RATE_LIMIT_ENABLED`
- `CTOA_TRUST_PROXY_HEADERS`
- `CTOA_CHAT_RATE_LIMIT_PER_MIN`
- `CTOA_AUTH_RATE_LIMIT_PER_MIN`
- `CTOA_READ_RATE_LIMIT_PER_MIN`
- `CTOA_AUDIT_LOG_FILE`
- `CTOA_SAFETY_TELEMETRY_FILE`
- `CTOA_SAFETY_ALERT_THRESHOLD`

## Behavior Rules

- Production must have a non-default `CTOA_JWT_SECRET`.
- Production public member self-registration is disabled unless
  `CTOA_API_SELF_REGISTER_ENABLED=true` and `CTOA_API_SELF_REGISTER_CODE` are
  configured.
- `/api/auth/register` cannot create `owner` or `operator` accounts without an
  authenticated owner token, even when the auth store is empty.
- Rate limiting is grouped by endpoint type.
- Rate limiting and HTTP audit IP identity use the socket client by default.
  `X-Forwarded-For` is trusted only when `CTOA_TRUST_PROXY_HEADERS=true`, and
  then only the first syntactically valid forwarded IP is accepted.
- Audit logging writes JSONL-style HTTP audit entries.
- HTTP audit entries redact token/password/API-key/Bearer forms and collapse
  local absolute paths in actor, IP, user-agent, request path, and nested meta
  before writing `CTOA_AUDIT_LOG_FILE`.
- Chat execution selects model/backend based on request complexity and route
  settings.
- Safety sanitizer records interventions and masks unsafe assistant claims.
- Release evidence reads from `CTOA_RELEASE_EVIDENCE_FILE` or default
  `runtime/release/latest-approval.json`, with bounded JSON reads,
  display-safe `evidence_path`, recursive token/password/API-key redaction, and
  local absolute path collapse before browser response.

## Test Guidance

When touching `api/main.py`, prefer targeted API tests for:

- auth required vs disabled
- role checks
- rate limit groups
- audit logging side effects
- chat model route selection
- safety sanitizer output
- release evidence missing/invalid/valid states
