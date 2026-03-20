-- CTOA Database Schema
-- Applied on first start via docker-entrypoint-initdb.d

SET client_min_messages = warning;

-- ─── Servers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS servers (
    id          SERIAL PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    name        TEXT,
    game_type   TEXT DEFAULT 'unknown',
    -- NEW → SCOUTING → INGESTED → READY → ERROR
    status      TEXT NOT NULL DEFAULT 'NEW',
    scout_error TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── API endpoints discovered per server ────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_endpoints (
    id              SERIAL PRIMARY KEY,
    server_id       INT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    path            TEXT NOT NULL,
    method          TEXT NOT NULL DEFAULT 'GET',
    last_status     INT,
    response_schema JSONB,
    last_checked    TIMESTAMPTZ,
    UNIQUE(server_id, path)
);

-- ─── Normalized game data ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS game_data (
    id          SERIAL PRIMARY KEY,
    server_id   INT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    -- monsters | items | players | events | server_info | highscores | guilds
    data_type   TEXT NOT NULL,
    raw         JSONB NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS game_data_server_type ON game_data(server_id, data_type);

-- ─── Generated modules / scripts ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS modules (
    id            SERIAL PRIMARY KEY,
    server_id     INT REFERENCES servers(id) ON DELETE SET NULL,
    task_id       TEXT NOT NULL UNIQUE,          -- MB-001, MB-042 …
    template      TEXT NOT NULL,
    output_file   TEXT,                           -- filename
    output_path   TEXT,                           -- full path on VPS
    -- QUEUED → GENERATED → VALIDATED → FAILED → RELEASED
    status        TEXT NOT NULL DEFAULT 'QUEUED',
    quality_score INT,                            -- 0-100
    test_log      TEXT,
    retry_count   INT NOT NULL DEFAULT 0,
    queued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    generated_at  TIMESTAMPTZ,
    validated_at  TIMESTAMPTZ
);

-- ─── Daily production stats + Launcher Day gate ──────────────────────────────
CREATE TABLE IF NOT EXISTS daily_stats (
    dt                  DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    modules_generated   INT  NOT NULL DEFAULT 0,
    programs_generated  INT  NOT NULL DEFAULT 0,
    avg_quality         FLOAT NOT NULL DEFAULT 0,
    launcher_day        BOOL NOT NULL DEFAULT FALSE,
    released_at         TIMESTAMPTZ
);

-- ─── Agent run audit log ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_runs (
    id          SERIAL PRIMARY KEY,
    agent       TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status      TEXT,           -- ok | error
    message     TEXT
);

-- ─── Registered user accounts (DB-backed auth) ────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    -- operator | owner
    role          TEXT NOT NULL DEFAULT 'operator',
    active        BOOL NOT NULL DEFAULT TRUE,
    created_by    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS accounts_updated_at ON accounts;
CREATE TRIGGER accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ─── User profiles (dashboard preferences per account) ─────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    username    TEXT PRIMARY KEY,
    role        TEXT NOT NULL,
    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- helper: update updated_at automatically
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS servers_updated_at ON servers;
CREATE TRIGGER servers_updated_at
    BEFORE UPDATE ON servers
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;
CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
