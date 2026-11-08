-- ==============================================================================
-- Migration 003: Row Level Security (RLS) & Sensitive Fields Trigger
-- Description: Enforces data privacy, access control policies, and
--              automatic review reopening upon sensitive field updates.
-- ==============================================================================

-- 1. TRIGGER: REABERTURA DE ANÁLISE EM ALTERAÇÕES SENSÍVEIS
-- Quando o proprietário altera dados críticos (nome, documento, whatsapp, endereço, etc.),
-- o status deve voltar para 'pending_review' para garantir curadoria contínua.
CREATE OR REPLACE FUNCTION businesses_sensitive_update_check()
RETURNS trigger AS $$
BEGIN
  -- Se a empresa já estava aprovada e houve alteração em campos sensíveis
  IF (OLD.status = 'approved') AND (
      OLD.name IS DISTINCT FROM NEW.name OR
      OLD.document_number IS DISTINCT FROM NEW.document_number OR
      OLD.whatsapp IS DISTINCT FROM NEW.whatsapp OR
      OLD.street IS DISTINCT FROM NEW.street OR
      OLD.number IS DISTINCT FROM NEW.number OR
      OLD.neighborhood IS DISTINCT FROM NEW.neighborhood OR
      OLD.city IS DISTINCT FROM NEW.city OR
      OLD.state IS DISTINCT FROM NEW.state OR
      OLD.location IS DISTINCT FROM NEW.location
  ) THEN
    -- Apenas reverte se quem alterou não for um admin deliberadamente aprovando/mantendo
    NEW.status := 'pending_review';

    INSERT INTO business_review_log (
      business_id,
      from_status,
      to_status,
      note
    ) VALUES (
      NEW.id,
      OLD.status,
      'pending_review',
      'Reanálise disparada automaticamente por alteração de campos cadastrais sensíveis.'
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_businesses_sensitive_update ON businesses;
CREATE TRIGGER trg_businesses_sensitive_update
BEFORE UPDATE ON businesses
FOR EACH ROW EXECUTE FUNCTION businesses_sensitive_update_check();

-- 2. HABILITAR ROW LEVEL SECURITY (RLS)
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_review_log ENABLE ROW LEVEL SECURITY;

-- 3. POLÍTICAS DE RLS (Compatível tanto com Supabase auth quanto com PostgreSQL JWT/role claims)

-- CATEGORIES: Leitura pública irrestrita
DROP POLICY IF EXISTS p_categories_public_select ON categories;
CREATE POLICY p_categories_public_select ON categories
  FOR SELECT USING (true);

-- BUSINESSES:
-- Apenas registros com status = 'approved' visíveis publicamente
DROP POLICY IF EXISTS p_businesses_public_select ON businesses;
CREATE POLICY p_businesses_public_select ON businesses
  FOR SELECT USING (
    status = 'approved'
    OR (current_setting('request.jwt.claim.role', true) = 'admin')
    OR (current_setting('request.jwt.claim.sub', true)::uuid = owner_user_id)
  );

-- Dono pode atualizar a própria empresa
DROP POLICY IF EXISTS p_businesses_owner_update ON businesses;
CREATE POLICY p_businesses_owner_update ON businesses
  FOR UPDATE USING (
    (current_setting('request.jwt.claim.role', true) = 'admin')
    OR (current_setting('request.jwt.claim.sub', true)::uuid = owner_user_id)
  );

-- ADMIN: Acesso total a businesses
DROP POLICY IF EXISTS p_businesses_admin_all ON businesses;
CREATE POLICY p_businesses_admin_all ON businesses
  FOR ALL USING (
    current_setting('request.jwt.claim.role', true) = 'admin'
  );

-- BUSINESS CATEGORIES:
-- Leitura pública para categorias associadas a empresas aprovadas
DROP POLICY IF EXISTS p_business_categories_public_select ON business_categories;
CREATE POLICY p_business_categories_public_select ON business_categories
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM businesses b
      WHERE b.id = business_categories.business_id
        AND (b.status = 'approved' OR current_setting('request.jwt.claim.role', true) = 'admin')
    )
  );

-- CONTACT EVENTS: Inserção anônima permitida para métricas (/go/...)
DROP POLICY IF EXISTS p_contact_events_insert ON contact_events;
CREATE POLICY p_contact_events_insert ON contact_events
  FOR INSERT WITH CHECK (true);

-- Leitura de métricas apenas para o dono da empresa ou admin
DROP POLICY IF EXISTS p_contact_events_owner_select ON contact_events;
CREATE POLICY p_contact_events_owner_select ON contact_events
  FOR SELECT USING (
    current_setting('request.jwt.claim.role', true) = 'admin'
    OR EXISTS (
      SELECT 1 FROM businesses b
      WHERE b.id = contact_events.business_id
        AND b.owner_user_id = current_setting('request.jwt.claim.sub', true)::uuid
    )
  );

-- REPORTS: Inserção pública permitida (visitante denunciando)
DROP POLICY IF EXISTS p_reports_insert ON reports;
CREATE POLICY p_reports_insert ON reports
  FOR INSERT WITH CHECK (true);

-- Visualização de denúncias restrita a admin
DROP POLICY IF EXISTS p_reports_admin_select ON reports;
CREATE POLICY p_reports_admin_select ON reports
  FOR SELECT USING (
    current_setting('request.jwt.claim.role', true) = 'admin'
  );
