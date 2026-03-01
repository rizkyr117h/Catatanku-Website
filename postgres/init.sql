-- ═══════════════════════════════════════════════════════════════
--  Catatanku — PostgreSQL Schema
-- ═══════════════════════════════════════════════════════════════

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- fast ILIKE search

-- ── USERS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::text,
    username     VARCHAR(64)  NOT NULL UNIQUE,
    email        VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);

-- ── REFRESH TOKENS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ  NOT NULL,
    revoked     BOOLEAN      NOT NULL DEFAULT FALSE,
    ip_address  VARCHAR(45),
    user_agent  VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rt_user_id    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_rt_token_hash ON refresh_tokens(token_hash);

-- ── TAGS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tags (
    id         VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id    VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(64) NOT NULL,
    color      VARCHAR(7)  NOT NULL DEFAULT '#4a6741',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_tag UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_tags_user_id ON tags(user_id);

-- ── NOTES ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notes (
    id         VARCHAR(36)  PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id    VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag_id     VARCHAR(36)  REFERENCES tags(id) ON DELETE SET NULL,
    title      VARCHAR(255) NOT NULL DEFAULT '',
    body       TEXT         NOT NULL DEFAULT '',
    pinned     BOOLEAN      NOT NULL DEFAULT FALSE,
    trash      BOOLEAN      NOT NULL DEFAULT FALSE,
    deadline   DATE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_user_id   ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_tag_id    ON notes(tag_id);
CREATE INDEX IF NOT EXISTS idx_notes_trash     ON notes(user_id, trash);
CREATE INDEX IF NOT EXISTS idx_notes_pinned    ON notes(user_id, pinned);
CREATE INDEX IF NOT EXISTS idx_notes_deadline  ON notes(user_id, deadline) WHERE deadline IS NOT NULL;

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_notes_title_trgm ON notes USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_notes_body_trgm  ON notes USING GIN (body  gin_trgm_ops);

-- ── TODO ITEMS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS todo_items (
    id         VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    note_id    VARCHAR(36) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    text       VARCHAR(512) NOT NULL,
    done       BOOLEAN     NOT NULL DEFAULT FALSE,
    position   INTEGER     NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_todo_note_id ON todo_items(note_id);

-- ── AUTO UPDATE updated_at TRIGGER ─────────────────────────────
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER set_updated_at_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE OR REPLACE TRIGGER set_updated_at_notes
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ── CLEANUP EXPIRED TOKENS (cron / pg_cron) ────────────────────
-- Run periodically: DELETE FROM refresh_tokens WHERE expires_at < NOW() OR revoked = TRUE;
