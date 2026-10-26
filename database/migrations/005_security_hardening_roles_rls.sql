-- ==============================================================================
-- Migration 005: Security Hardening - FORCE RLS, Database Roles & Transaction Context
-- Description: Enforces strict row level security (even for table owners),
--              establishes app_rw/migrator/readonly roles, and rewrites
--              RLS policies to use application-level session settings.
-- ==============================================================================

-- 1. HABILITAR FORCE ROW LEVEL SECURITY (C3)
-- Garante que as políticas de RLS sejam aplicadas mesmo ao conectar como dono das tabelas.
ALTER TABLE businesses FORCE ROW LEVEL SECURITY;
ALTER TABLE categories FORCE ROW LEVEL SECURITY;
ALTER TABLE business_categories FORCE ROW LEVEL SECURITY;
ALTER TABLE contact_events FORCE ROW LEVEL SECURITY;
ALTER TABLE reports FORCE ROW LEVEL SECURITY;
ALTER TABLE invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE business_review_log FORCE ROW LEVEL SECURITY;

-- 2. CRIAÇÃO SEGURA DE ROLES DO BANCO DE DADOS
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
    CREATE ROLE app_rw NOSUPERUSER NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'migrator') THEN
    CREATE ROLE migrator NOSUPERUSER;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly') THEN
    CREATE ROLE readonly NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;

-- Statement timeout de 5 segundos para a aplicação (evita DoS por queries presas)
ALTER ROLE app_rw SET statement_timeout = '5s';

-- Permissões do role de aplicação (app_rw)
GRANT USAGE ON SCHEMA public TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rw;

-- Append-only: impede app_rw de alterar ou apagar logs de auditoria
REVOKE UPDATE, DELETE ON business_review_log FROM app_rw;

-- 3. POLÍTICAS DE RLS REESCRITAS COM CONTEXTO DA APLICAÇÃO (SET LOCAL app.*)

-- BUSINESSES
DROP POLICY IF EXISTS p_businesses_public_select ON businesses;
CREATE POLICY p_businesses_public_select ON businesses
  FOR SELECT USING (
    status = 'approved'
    OR current_setting('app.role', true) = 'admin'
    OR (
      current_setting('app.user_id', true) IS NOT NULL 
      AND current_setting('app.user_id', true) ~ '^[0-9a-fA-F-]{36}$'
      AND current_setting('app.user_id', true)::uuid = owner_user_id
    )
  );

DROP POLICY IF EXISTS p_businesses_owner_update ON businesses;
CREATE POLICY p_businesses_owner_update ON businesses
  FOR UPDATE USING (
    current_setting('app.role', true) = 'admin'
    OR (
      current_setting('app.user_id', true) IS NOT NULL
      AND current_setting('app.user_id', true) ~ '^[0-9a-fA-F-]{36}$'
      AND current_setting('app.user_id', true)::uuid = owner_user_id
    )
  );

-- BUSINESS REVIEW LOG (Auditoria: somente admin visualiza; somente admin insere)
DROP POLICY IF EXISTS p_business_review_log_select ON business_review_log;
CREATE POLICY p_business_review_log_select ON business_review_log
  FOR SELECT USING (
    current_setting('app.role', true) = 'admin'
  );

DROP POLICY IF EXISTS p_business_review_log_insert ON business_review_log;
CREATE POLICY p_business_review_log_insert ON business_review_log
  FOR INSERT WITH CHECK (
    current_setting('app.role', true) = 'admin'
  );

-- INVITATIONS (Somente admin gerencia e consulta convites com token)
DROP POLICY IF EXISTS p_invitations_admin_all ON invitations;
CREATE POLICY p_invitations_admin_all ON invitations
  FOR ALL USING (
    current_setting('app.role', true) = 'admin'
  );

-- REPORTS (Visitante anônimo pode denunciar; somente admin visualiza)
DROP POLICY IF EXISTS p_reports_admin_select ON reports;
CREATE POLICY p_reports_admin_select ON reports
  FOR SELECT USING (
    current_setting('app.role', true) = 'admin'
  );
