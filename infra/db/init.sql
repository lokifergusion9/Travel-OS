-- Runs once on first DB init (as the superuser) via /docker-entrypoint-initdb.d.
-- Creates a dedicated NON-superuser application role so Postgres RLS policies
-- are actually enforced (superusers and BYPASSRLS roles ignore RLS).

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travelos_app') THEN
      CREATE ROLE travelos_app LOGIN PASSWORD 'travelos_app';
   END IF;
END
$$;

-- App role owns the schema so Alembic (run as travelos_app) can manage tables.
ALTER SCHEMA public OWNER TO travelos_app;
GRANT ALL ON SCHEMA public TO travelos_app;
GRANT ALL PRIVILEGES ON DATABASE travelos TO travelos_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO travelos_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO travelos_app;

-- pgvector (needs superuser; used from Phase 1 for RAG over itineraries/hotels).
CREATE EXTENSION IF NOT EXISTS vector;
