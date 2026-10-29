-- ==============================================================================
-- SCRIPT UNIFICADO DE RESET COMPLETO - PATRIOTAIN DICA
-- Limpa o schema public e aplica todas as 19 migrações e sementes iniciais
-- ==============================================================================

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO public;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(150) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    checksum VARCHAR(64) NOT NULL
);

-- >>> MIGRAÇÃO: 001_initial_schema.sql >>>
-- ==============================================================================
-- Migration 001: Initial Schema
-- Description: Core tables, enums, extensions, indices, and triggers for
--              the Curated Local Marketplace (MVP).
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- 2. ENUMS
DO $$ BEGIN
  CREATE TYPE business_status AS ENUM (
    'draft',
    'pending_review',
    'needs_info',
    'approved',
    'rejected',
    'suspended'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE business_source AS ENUM (
    'seeded',
    'invited',
    'application',
    'claimed'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE listing_type AS ENUM (
    'service',
    'product',
    'both'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE service_mode AS ENUM (
    'at_location',
    'at_customer',
    'both',
    'online'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- 3. USERS TABLE (Auth próprio para arquitetura FastAPI / Next.js)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  phone VARCHAR(20),
  role VARCHAR(20) NOT NULL DEFAULT 'user', -- 'admin', 'owner', 'user'
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- 4. CATEGORIES TABLE
CREATE TABLE IF NOT EXISTS categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
  name VARCHAR(100) NOT NULL UNIQUE,
  slug VARCHAR(100) NOT NULL UNIQUE,
  kind listing_type NOT NULL DEFAULT 'both',
  icon_name VARCHAR(50),
  display_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug);
CREATE INDEX IF NOT EXISTS idx_categories_kind ON categories (kind);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories (parent_id);

-- 5. BUSINESSES TABLE
CREATE TABLE IF NOT EXISTS businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  name VARCHAR(150) NOT NULL,
  slug VARCHAR(180) NOT NULL UNIQUE,
  description TEXT,
  listing_type listing_type NOT NULL DEFAULT 'service',

  -- Identificação cadastral (uso interno administrativo, não exposto publicamente)
  document_type VARCHAR(4),                       -- 'CNPJ' ou 'CPF'
  document_number VARCHAR(14) UNIQUE,
  cnpj_situation VARCHAR(50),                     -- Status do CNPJ (ex: ATIVA, BAIXADA)
  cnpj_checked_at TIMESTAMPTZ,

  -- Contatos
  whatsapp VARCHAR(20) NOT NULL,
  whatsapp_verified_at TIMESTAMPTZ,
  phone VARCHAR(20),
  website VARCHAR(255),
  instagram VARCHAR(100),

  -- Localização
  street VARCHAR(255),
  number VARCHAR(50),
  neighborhood VARCHAR(100) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state VARCHAR(2) NOT NULL,
  postal_code VARCHAR(10),
  show_full_address BOOLEAN NOT NULL DEFAULT FALSE,
  location GEOGRAPHY(Point, 4326) NOT NULL,
  service_mode service_mode NOT NULL DEFAULT 'at_location',
  service_radius_km INT,                          -- Raio atendido para at_customer / both

  -- Mídia
  logo_url TEXT,
  banner_url TEXT,

  -- Curadoria e Triagem
  status business_status NOT NULL DEFAULT 'pending_review',
  source business_source NOT NULL DEFAULT 'application',
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,     -- Selo "Verificada"
  rejection_reason TEXT,
  reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,

  -- Busca Textual Full-Text Search
  search_vector TSVECTOR,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices essenciais para performance e geo-queries
CREATE INDEX IF NOT EXISTS idx_businesses_location ON businesses USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_businesses_status ON businesses (status);
CREATE INDEX IF NOT EXISTS idx_businesses_city_state ON businesses (state, city);
CREATE INDEX IF NOT EXISTS idx_businesses_search ON businesses USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_businesses_name_trgm ON businesses USING GIN(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_businesses_slug ON businesses (slug);
CREATE INDEX IF NOT EXISTS idx_businesses_owner ON businesses (owner_user_id);

-- 6. BUSINESS CATEGORIES (N:N com indicação de primária)
CREATE TABLE IF NOT EXISTS business_categories (
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  category_id UUID REFERENCES categories(id) ON DELETE RESTRICT,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (business_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_business_categories_category ON business_categories (category_id);
CREATE INDEX IF NOT EXISTS idx_business_categories_business ON business_categories (business_id);

-- 7. AUDITORIA E LOG DA TRIAGEM
CREATE TABLE IF NOT EXISTS business_review_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  from_status business_status,
  to_status business_status NOT NULL,
  note TEXT,
  admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_log_business ON business_review_log (business_id);
CREATE INDEX IF NOT EXISTS idx_review_log_created_at ON business_review_log (created_at DESC);

-- 8. CONVITES (Canal B)
CREATE TABLE IF NOT EXISTS invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token VARCHAR(64) NOT NULL UNIQUE,
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  phone VARCHAR(20),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations (token);
CREATE INDEX IF NOT EXISTS idx_invitations_business ON invitations (business_id);

-- 9. EVENTOS DE CONTATO E MÉTRICAS DE CONVERSÃO
CREATE TABLE IF NOT EXISTS contact_events (
  id BIGSERIAL PRIMARY KEY,
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  event_type VARCHAR(20) NOT NULL, -- 'whatsapp', 'phone', 'website', 'profile_view'
  city VARCHAR(100),
  referrer TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contact_events_business ON contact_events (business_id, created_at);
CREATE INDEX IF NOT EXISTS idx_contact_events_type ON contact_events (event_type, created_at);

-- 10. DENÚNCIAS DE USUÁRIOS
CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  reason VARCHAR(100) NOT NULL,
  details TEXT,
  contact_email VARCHAR(255),
  status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'resolved', 'dismissed'
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status);
CREATE INDEX IF NOT EXISTS idx_reports_business ON reports (business_id);

-- 11. TRIGGER: ATUALIZA SEARCH_VECTOR (nome + descrição, português, unaccent)
CREATE OR REPLACE FUNCTION businesses_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('portuguese', unaccent(coalesce(NEW.name, ''))), 'A') ||
    setweight(to_tsvector('portuguese', unaccent(coalesce(NEW.description, ''))), 'B');
  NEW.updated_at := NOW();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_businesses_search_vector ON businesses;
CREATE TRIGGER trg_businesses_search_vector
BEFORE INSERT OR UPDATE ON businesses
FOR EACH ROW EXECUTE FUNCTION businesses_search_vector_update();

INSERT INTO schema_migrations (version, checksum) VALUES ('001_initial_schema.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 002_search_function.sql >>>
-- ==============================================================================
-- Migration 002: Spatial Search Function (PostGIS)
-- Description: Implements get_nearby_businesses function with PostGIS KNN
--              ordering, service area coverage, full-text and trigram search.
-- ==============================================================================

CREATE OR REPLACE FUNCTION get_nearby_businesses(
  user_lat DOUBLE PRECISION,
  user_lng DOUBLE PRECISION,
  max_distance_km DOUBLE PRECISION DEFAULT 50.0,
  search_query TEXT DEFAULT NULL,
  filter_category UUID DEFAULT NULL,
  filter_type listing_type DEFAULT NULL,
  page_limit INT DEFAULT 20,
  page_offset INT DEFAULT 0
)
RETURNS TABLE (
  id UUID,
  name VARCHAR,
  slug VARCHAR,
  description TEXT,
  listing_type listing_type,
  service_mode service_mode,
  service_radius_km INT,
  category_name VARCHAR,
  whatsapp VARCHAR,
  phone VARCHAR,
  neighborhood VARCHAR,
  city VARCHAR,
  state VARCHAR,
  street VARCHAR,
  number VARCHAR,
  show_full_address BOOLEAN,
  logo_url TEXT,
  banner_url TEXT,
  is_verified BOOLEAN,
  distance_km DOUBLE PRECISION
)
LANGUAGE sql STABLE AS $$
  WITH u AS (
    SELECT ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography AS p
  )
  SELECT
    b.id,
    b.name,
    b.slug,
    b.description,
    b.listing_type,
    b.service_mode,
    b.service_radius_km,
    c.name AS category_name,
    b.whatsapp,
    b.phone,
    b.neighborhood,
    b.city,
    b.state,
    CASE WHEN b.show_full_address THEN b.street ELSE NULL END AS street,
    CASE WHEN b.show_full_address THEN b.number ELSE NULL END AS number,
    b.show_full_address,
    b.logo_url,
    b.banner_url,
    b.is_verified,
    ROUND((ST_Distance(b.location, u.p) / 1000)::numeric, 1)::DOUBLE PRECISION AS distance_km
  FROM businesses b
  CROSS JOIN u
  LEFT JOIN business_categories bc ON bc.business_id = b.id AND bc.is_primary
  LEFT JOIN categories c ON c.id = bc.category_id
  WHERE b.status = 'approved'
    AND (
      -- 1. Empresas fisicamente dentro do raio máximo de busca
      ST_DWithin(b.location, u.p, max_distance_km * 1000)
      -- 2. OU empresas cujo raio de atendimento a domicílio cobre o usuário
      OR (
        b.service_mode IN ('at_customer', 'both')
        AND b.service_radius_km IS NOT NULL
        AND ST_DWithin(b.location, u.p, b.service_radius_km * 1000)
      )
      -- 3. OU empresas com atendimento 100% online
      OR (b.service_mode = 'online')
    )
    -- Filtro por tipo (serviço / produto)
    AND (filter_type IS NULL OR b.listing_type = filter_type OR b.listing_type = 'both')
    -- Filtro por categoria (via tabela de relacionamento N:N)
    AND (
      filter_category IS NULL OR EXISTS (
        SELECT 1 FROM business_categories x
        WHERE x.business_id = b.id AND x.category_id = filter_category
      )
    )
    -- Busca textual inteligente: Full-Text search em português sem acento + Trigram para tolerância a digitação
    AND (
      search_query IS NULL
      OR search_query = ''
      OR b.search_vector @@ websearch_to_tsquery('portuguese', unaccent(search_query))
      OR b.name % search_query
      OR EXISTS (
        SELECT 1 FROM business_categories bc_search
        JOIN categories c_search ON c_search.id = bc_search.category_id
        WHERE bc_search.business_id = b.id
          AND (c_search.name % search_query OR unaccent(c_search.name) ILIKE unaccent('%' || search_query || '%'))
      )
    )
  ORDER BY
    -- Ordenação por proximidade usando índice espacial GIST e operador KNN (<->)
    b.location <-> u.p
  LIMIT page_limit OFFSET page_offset;
$$;

INSERT INTO schema_migrations (version, checksum) VALUES ('002_search_function.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 003_rls_and_permissions.sql >>>
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

INSERT INTO schema_migrations (version, checksum) VALUES ('003_rls_and_permissions.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 004_seed_categories.sql >>>
-- ==============================================================================
-- Migration 004 / Seed: Initial Curated Categories
-- Description: Core taxonomy of local services, products, and hybrid businesses
--              tailored for Brazilian municipal launch (MVP).
-- ==============================================================================

INSERT INTO categories (name, slug, kind, icon_name, display_order)
VALUES
  -- 1. SERVIÇOS RESIDENCIAIS E REPAROS
  ('Eletricista', 'eletricista', 'service', 'zap', 1),
  ('Encanador e Desentupidora', 'encanador-desentupidora', 'service', 'droplets', 2),
  ('Ar-condicionado e Climatização', 'ar-condicionado-climatizacao', 'service', 'wind', 3),
  ('Pintor e Reformas', 'pintor-reformas', 'service', 'paint-brush', 4),
  ('Chaveiro 24h', 'chaveiro', 'service', 'key', 5),
  ('Marcenaria e Móveis Planejados', 'marcenaria', 'service', 'hammer', 6),
  ('Serralheria e Esquadrias', 'serralheria', 'service', 'shield', 7),
  ('Vidraçaria', 'vidracaria', 'service', 'square', 8),
  ('Diarista e Limpeza Profissional', 'diarista-limpeza', 'service', 'sparkles', 9),
  ('Dedetizadora e Controle de Pragas', 'dedetizadora', 'service', 'shield-alert', 10),
  ('Jardinagem e Paisagismo', 'jardinagem', 'service', 'flower-2', 11),
  ('Fretes e Mudanças', 'fretes-mudancas', 'service', 'truck', 12),

  -- 2. AUTOMOTIVO
  ('Mecânica e Autoelétrica', 'mecanica-autoeletrica', 'service', 'car', 13),
  ('Funilaria e Pintura Automotiva', 'funilaria-pintura', 'service', 'gauge', 14),
  ('Borracharia e Pneus', 'borracharia-pneus', 'service', 'disc', 15),
  ('Lava-Rápido e Estética Automotiva', 'lava-rapido', 'service', 'waves', 16),

  -- 3. TECNOLOGIA E MANUTENÇÃO
  ('Assistência de Celulares e Tablets', 'celulares-tablets', 'service', 'smartphone', 17),
  ('Manutenção de Computadores e Redes', 'informatica-redes', 'service', 'laptop', 18),
  ('Instalação de Câmeras e Segurança', 'seguranca-eletronica', 'service', 'cctv', 19),

  -- 4. SAÚDE, BELEZA E BEM-ESTAR
  ('Barbearia e Salão de Beleza', 'barbearia-salao', 'both', 'scissors', 20),
  ('Estética e Cuidados Pessoais', 'estetica-beleza', 'both', 'sparkle', 21),
  ('Personal Trainer e Fisioterapia', 'personal-fisioterapia', 'service', 'activity', 22),

  -- 5. PETS
  ('Pet Shop e Banho & Tosa', 'pet-shop-banho-tosa', 'both', 'paw-print', 23),
  ('Clínica Veterinária', 'veterinaria', 'service', 'stethoscope', 24),

  -- 6. ALIMENTAÇÃO E PRODUTOS LOCAIS
  ('Marmitas e Comida Caseira', 'marmitas-alimentacao', 'product', 'utensils', 25),
  ('Padaria e Confeitaria Artesanal', 'padaria-confeitaria', 'product', 'cake', 26),
  ('Hortifruti e Orgânicos', 'hortifruti-organicos', 'product', 'apple', 27),
  ('Água Mineral e Gás', 'agua-gas', 'product', 'flame', 28),

  -- 7. COMÉRCIO E MATERIAIS
  ('Materiais de Construção', 'materiais-construcao', 'both', 'hard-hat', 29),
  ('Flores e Plantas Ornamentais', 'floricultura', 'product', 'leaf', 30),
  ('Costura e Ajustes', 'costura-ajustes', 'service', 'needle', 31),
  ('Papelaria e Presentes', 'papelaria-presentes', 'product', 'book-open', 32),

  -- 8. SERVIÇOS PROFISSIONAIS E ESPECIALIZADOS
  ('Advocacia e Assessoria Jurídica', 'advocacia-juridico', 'service', 'scale', 33),
  ('Contabilidade e Finanças', 'contabilidade-fiscal', 'service', 'calculator', 34),
  ('Despachante Documentalista', 'despachante', 'service', 'file-text', 35),
  ('Psicologia e Saúde Mental', 'psicologia-saude-mental', 'service', 'brain', 36),
  ('Fisioterapia e Reabilitação', 'fisioterapia-reabilitacao', 'service', 'activity', 37),
  ('Odontologia e Dentista', 'odontologia-dentista', 'service', 'smile', 38),
  ('Nutrição e Dietética', 'nutricao-bem-estar', 'service', 'apple', 39),
  ('Manicure, Pedicure e Nail Art', 'manicure-pedicure', 'service', 'sparkles', 40),
  ('Sobrancelhas e Cílios', 'sobrancelhas-cilios', 'service', 'eye', 41),
  ('Tatuagem e Piercing', 'tatuagem-piercing', 'service', 'feather', 42),
  ('Fotografia e Filmagem', 'fotografia-filmagem', 'service', 'camera', 43),
  ('Festas, Decoração e Eventos', 'festas-eventos', 'service', 'gift', 44),
  ('DJ, Som e Iluminação', 'dj-som-iluminacao', 'service', 'music', 45),
  ('Aulas Particulares e Educação', 'aulas-particulares', 'service', 'graduation-cap', 46),
  ('Conserto de Eletrodomésticos', 'conserto-eletrodomesticos', 'service', 'wrench', 47),
  ('Tapeçaria e Reforma de Estofados', 'tapecaria-estofados', 'service', 'armchair', 48),
  ('Guincho e Reboque 24h', 'guincho-reboque-24h', 'service', 'truck', 49),
  ('Adestramento e Passeador Pet', 'adestramento-passeador-pet', 'service', 'paw-print', 50),
  ('Gesso, Drywall e Iluminação', 'gesso-drywall', 'service', 'layout', 51),
  ('Energia Solar e Fotovoltaica', 'energia-solar', 'service', 'sun', 52),
  ('Pizzaria e Hamburgueria', 'pizzaria-hamburgueria', 'both', 'pizza', 53),
  ('Gráfica Rápida e Comunicação Visual', 'grafica-comunicacao-visual', 'service', 'printer', 54)
ON CONFLICT (slug) DO UPDATE
SET
  name = EXCLUDED.name,
  kind = EXCLUDED.kind,
  icon_name = EXCLUDED.icon_name,
  display_order = EXCLUDED.display_order;


INSERT INTO schema_migrations (version, checksum) VALUES ('004_seed_categories.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 005_security_hardening_roles_rls.sql >>>
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

INSERT INTO schema_migrations (version, checksum) VALUES ('005_security_hardening_roles_rls.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 006_national_search_and_geocoding.sql >>>
-- ==============================================================================
-- Migration 006: National Search, Dynamic Geocoding and Location Nullability
-- Description:
-- 1. Permite empresas 100% online ou em triagem sem coordenadas fixas
-- 2. Adiciona colunas geocode_source e geocode_confidence
-- 3. Atualiza get_nearby_businesses para suportar busca nacional (quando lat/lng são NULL)
-- ==============================================================================

-- 1. Tornar location anulável para suportar empresas online e geocodificação pendente
ALTER TABLE businesses ALTER COLUMN location DROP NOT NULL;

-- 2. Colunas de auditoria da geocodificação server-side (H4)
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS geocode_source VARCHAR(50);
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS geocode_confidence FLOAT;

-- 3. Função aprimorada para busca nacional ou por proximidade
CREATE OR REPLACE FUNCTION get_nearby_businesses(
  user_lat DOUBLE PRECISION DEFAULT NULL,
  user_lng DOUBLE PRECISION DEFAULT NULL,
  max_distance_km DOUBLE PRECISION DEFAULT 50.0,
  search_query TEXT DEFAULT NULL,
  filter_category UUID DEFAULT NULL,
  filter_type listing_type DEFAULT NULL,
  page_limit INT DEFAULT 20,
  page_offset INT DEFAULT 0,
  filter_state VARCHAR(2) DEFAULT NULL,
  filter_city VARCHAR(100) DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  name VARCHAR,
  slug VARCHAR,
  description TEXT,
  listing_type listing_type,
  service_mode service_mode,
  service_radius_km INT,
  category_name VARCHAR,
  whatsapp VARCHAR,
  phone VARCHAR,
  neighborhood VARCHAR,
  city VARCHAR,
  state VARCHAR,
  street VARCHAR,
  number VARCHAR,
  show_full_address BOOLEAN,
  logo_url TEXT,
  banner_url TEXT,
  is_verified BOOLEAN,
  distance_km DOUBLE PRECISION
)
LANGUAGE sql STABLE AS $$
  WITH u AS (
    SELECT 
      CASE 
        WHEN user_lat IS NOT NULL AND user_lng IS NOT NULL 
        THEN ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography 
        ELSE NULL 
      END AS p
  )
  SELECT
    b.id,
    b.name,
    b.slug,
    b.description,
    b.listing_type,
    b.service_mode,
    b.service_radius_km,
    c.name AS category_name,
    b.whatsapp,
    b.phone,
    b.neighborhood,
    b.city,
    b.state,
    CASE WHEN b.show_full_address THEN b.street ELSE NULL END AS street,
    CASE WHEN b.show_full_address THEN b.number ELSE NULL END AS number,
    b.show_full_address,
    b.logo_url,
    b.banner_url,
    b.is_verified,
    CASE 
      WHEN u.p IS NOT NULL AND b.location IS NOT NULL 
      THEN ROUND((ST_Distance(b.location, u.p) / 1000)::numeric, 1)::DOUBLE PRECISION 
      ELSE NULL 
    END AS distance_km
  FROM businesses b
  CROSS JOIN u
  LEFT JOIN business_categories bc ON bc.business_id = b.id AND bc.is_primary
  LEFT JOIN categories c ON c.id = bc.category_id
  WHERE b.status = 'approved'
    -- Cobertura espacial / modalidade de serviço
    AND (
      -- Se usuário forneceu lat/lng, aplica critérios espaciais
      (u.p IS NOT NULL AND b.location IS NOT NULL AND (
        ST_DWithin(b.location, u.p, max_distance_km * 1000)
        OR (b.service_mode IN ('at_customer', 'both') AND b.service_radius_km IS NOT NULL AND ST_DWithin(b.location, u.p, b.service_radius_km * 1000))
        OR (b.service_mode = 'online')
      ))
      -- Se busca é nacional (sem lat/lng)
      OR (u.p IS NULL)
      -- Empresas 100% online sempre elegíveis
      OR (b.service_mode = 'online')
    )
    -- Filtros geográficos opcionais (Estado e Cidade)
    AND (filter_state IS NULL OR UPPER(b.state) = UPPER(filter_state))
    AND (filter_city IS NULL OR unaccent(b.city) ILIKE unaccent('%' || filter_city || '%'))
    -- Filtro por tipo (serviço / produto)
    AND (filter_type IS NULL OR b.listing_type = filter_type OR b.listing_type = 'both')
    -- Filtro por categoria
    AND (
      filter_category IS NULL OR EXISTS (
        SELECT 1 FROM business_categories x
        WHERE x.business_id = b.id AND x.category_id = filter_category
      )
    )
    -- Busca textual
    AND (
      search_query IS NULL
      OR search_query = ''
      OR b.search_vector @@ websearch_to_tsquery('portuguese', unaccent(search_query))
      OR b.name % search_query
      OR EXISTS (
        SELECT 1 FROM business_categories bc_search
        JOIN categories c_search ON c_search.id = bc_search.category_id
        WHERE bc_search.business_id = b.id
          AND (c_search.name % search_query OR unaccent(c_search.name) ILIKE unaccent('%' || search_query || '%'))
      )
    )
  ORDER BY
    b.is_verified DESC,
    CASE WHEN u.p IS NOT NULL AND b.location IS NOT NULL THEN ST_Distance(b.location, u.p) END ASC NULLS LAST,
    b.created_at DESC
  LIMIT page_limit
  OFFSET page_offset;
$$;

INSERT INTO schema_migrations (version, checksum) VALUES ('006_national_search_and_geocoding.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 007_dynamic_niches_and_aliases.sql >>>
-- ==============================================================================
-- Migration 007: Dynamic Niches, Aliases and Moderation (Sec. 4)
-- Description:
-- 1. Suporte a nichos de cauda longa propostos por usuários
-- 2. Status 'approved', 'pending', 'rejected' para categorias
-- 3. Tabela category_aliases para sinônimos e mesclagem de nichos pelo Admin
-- ==============================================================================

-- 1. Colunas de moderação de nichos dinâmicos
ALTER TABLE categories ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';
ALTER TABLE categories ADD COLUMN IF NOT EXISTS proposed_by_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL;

-- 2. Tabela de Aliases (Sinônimos) para Autocomplete e Mesclagem
CREATE TABLE IF NOT EXISTS category_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  alias_name VARCHAR(100) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_category_aliases_name ON category_aliases (alias_name);
CREATE INDEX IF NOT EXISTS idx_categories_status ON categories (status);

INSERT INTO schema_migrations (version, checksum) VALUES ('007_dynamic_niches_and_aliases.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 008_owner_pending_changes_and_invitations.sql >>>
-- ==============================================================================
-- Migration 008: Owner Pending Changes and Secure Token Invitations
-- Description:
-- 1. [H3] business_pending_changes: dono propõe alterações em campos de risco
--    sem despublicar a versão aprovada e sem bypass de triagem.
-- 2. [M12] invitations: convites criptográficos baseados em SHA-256 (sem tokens em texto claro).
-- ==============================================================================

-- 1. Tabela de Alterações Pendentes do Dono (H3)
CREATE TABLE IF NOT EXISTS business_pending_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  proposed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  changes JSONB NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
  reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  rejection_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_changes_business ON business_pending_changes(business_id);
CREATE INDEX IF NOT EXISTS idx_pending_changes_status ON business_pending_changes(status);

-- 2. Tabela de Convites Seguros (M12)
CREATE TABLE IF NOT EXISTS invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  phone VARCHAR(20),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_token_hash ON invitations(token_hash);
CREATE INDEX IF NOT EXISTS idx_invitations_business ON invitations(business_id);

INSERT INTO schema_migrations (version, checksum) VALUES ('008_owner_pending_changes_and_invitations.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 009_lgpd_consent_and_requests.sql >>>
-- Migration 009: Registro de solicitacoes de privacidade e direitos do titular (LGPD M11)
CREATE TABLE IF NOT EXISTS data_subject_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(32) NOT NULL, -- 'deletion', 'revocation', 'export', 'correction', 'information'
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(32),
    details TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'received', -- 'received', 'processing', 'completed', 'rejected'
    ip_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_data_subject_requests_email ON data_subject_requests(email);
CREATE INDEX IF NOT EXISTS idx_data_subject_requests_status ON data_subject_requests(status);

INSERT INTO schema_migrations (version, checksum) VALUES ('009_lgpd_consent_and_requests.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 010_user_security_columns.sql >>>
-- Migration 010: Colunas de seguranca da tabela users (C1, C2)
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;

INSERT INTO schema_migrations (version, checksum) VALUES ('010_user_security_columns.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 011_service_modes_multi_selection.sql >>>
-- Migration 011: Multi-seleção de Métodos de Atendimento (Presencial, Domicílio e Online)
-- Permite que uma empresa atue em qualquer combinação dos 3 canais simultaneamente.

ALTER TABLE businesses 
  ADD COLUMN IF NOT EXISTS serves_at_location BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS serves_at_customer BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS serves_online BOOLEAN NOT NULL DEFAULT FALSE;

-- Retrocompatibilidade: Preencher as novas colunas com base no service_mode existente
UPDATE businesses SET
  serves_at_location = (service_mode IN ('at_location', 'both')),
  serves_at_customer = (service_mode IN ('at_customer', 'both')),
  serves_online = (service_mode = 'online');

-- Índices parciais para otimizar buscas por método de atendimento
CREATE INDEX IF NOT EXISTS idx_businesses_serves_at_location ON businesses(serves_at_location) WHERE status = 'approved';
CREATE INDEX IF NOT EXISTS idx_businesses_serves_at_customer ON businesses(serves_at_customer) WHERE status = 'approved';
CREATE INDEX IF NOT EXISTS idx_businesses_serves_online ON businesses(serves_online) WHERE status = 'approved';

-- Atualização da função search_businesses para considerar as novas colunas
CREATE OR REPLACE FUNCTION search_businesses(
  user_lat DOUBLE PRECISION,
  user_lng DOUBLE PRECISION,
  max_distance_km DOUBLE PRECISION DEFAULT 20.0,
  filter_category UUID DEFAULT NULL,
  filter_type listing_type DEFAULT NULL,
  filter_state VARCHAR DEFAULT NULL,
  filter_city VARCHAR DEFAULT NULL,
  search_query VARCHAR DEFAULT NULL,
  page_offset INT DEFAULT 0,
  page_limit INT DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  name VARCHAR,
  slug VARCHAR,
  description TEXT,
  listing_type listing_type,
  service_mode service_mode,
  service_radius_km INT,
  serves_at_location BOOLEAN,
  serves_at_customer BOOLEAN,
  serves_online BOOLEAN,
  category_name VARCHAR,
  whatsapp VARCHAR,
  phone VARCHAR,
  neighborhood VARCHAR,
  city VARCHAR,
  state VARCHAR,
  street VARCHAR,
  number VARCHAR,
  show_full_address BOOLEAN,
  logo_url TEXT,
  banner_url TEXT,
  is_verified BOOLEAN,
  distance_km DOUBLE PRECISION
)
LANGUAGE sql STABLE AS $$
  WITH u AS (
    SELECT 
      CASE 
        WHEN user_lat IS NOT NULL AND user_lng IS NOT NULL 
        THEN ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)::geography 
        ELSE NULL 
      END AS p
  )
  SELECT
    b.id,
    b.name,
    b.slug,
    b.description,
    b.listing_type,
    b.service_mode,
    b.service_radius_km,
    b.serves_at_location,
    b.serves_at_customer,
    b.serves_online,
    c.name AS category_name,
    b.whatsapp,
    b.phone,
    b.neighborhood,
    b.city,
    b.state,
    CASE WHEN b.show_full_address THEN b.street ELSE NULL END AS street,
    CASE WHEN b.show_full_address THEN b.number ELSE NULL END AS number,
    b.show_full_address,
    b.logo_url,
    b.banner_url,
    b.is_verified,
    CASE 
      WHEN u.p IS NOT NULL AND b.location IS NOT NULL 
      THEN ROUND((ST_Distance(b.location, u.p) / 1000)::numeric, 1)::DOUBLE PRECISION 
      ELSE NULL 
    END AS distance_km
  FROM businesses b
  CROSS JOIN u
  LEFT JOIN business_categories bc ON bc.business_id = b.id AND bc.is_primary
  LEFT JOIN categories c ON c.id = bc.category_id
  WHERE b.status = 'approved'
    -- Cobertura espacial / modalidade de serviço multi-canal
    AND (
      -- Se usuário forneceu lat/lng, atende se:
      -- 1. Estabelecimento físico dentro do raio máximo OU
      -- 2. Domicílio cobre o usuário (raio de atendimento da empresa) OU
      -- 3. Atende online
      (u.p IS NOT NULL AND (
        (b.location IS NOT NULL AND b.serves_at_location AND ST_DWithin(b.location, u.p, max_distance_km * 1000))
        OR (b.location IS NOT NULL AND b.serves_at_customer AND b.service_radius_km IS NOT NULL AND ST_DWithin(b.location, u.p, b.service_radius_km * 1000))
        OR (b.serves_online)
      ))
      -- Se busca é nacional (sem lat/lng)
      OR (u.p IS NULL)
      -- Empresas com atendimento online sempre elegíveis
      OR (b.serves_online)
    )
    -- Filtros geográficos opcionais (Estado e Cidade)
    AND (filter_state IS NULL OR UPPER(b.state) = UPPER(filter_state))
    AND (filter_city IS NULL OR unaccent(b.city) ILIKE unaccent('%' || filter_city || '%'))
    -- Filtro por tipo (serviço / produto)
    AND (filter_type IS NULL OR b.listing_type = filter_type OR b.listing_type = 'both')
    -- Filtro por categoria
    AND (
      filter_category IS NULL OR EXISTS (
        SELECT 1 FROM business_categories x
        WHERE x.business_id = b.id AND x.category_id = filter_category
      )
    )
    -- Busca textual
    AND (
      search_query IS NULL
      OR search_query = ''
      OR b.search_vector @@ websearch_to_tsquery('portuguese', unaccent(search_query))
      OR b.name % search_query
      OR EXISTS (
        SELECT 1 FROM business_categories bc_search
        JOIN categories c_search ON c_search.id = bc_search.category_id
        WHERE bc_search.business_id = b.id
          AND (c_search.name % search_query OR unaccent(c_search.name) ILIKE unaccent('%' || search_query || '%'))
      )
    )
  ORDER BY
    b.is_verified DESC,
    CASE WHEN u.p IS NOT NULL AND b.location IS NOT NULL THEN ST_Distance(b.location, u.p) END ASC NULLS LAST,
    b.created_at DESC
  LIMIT page_limit
  OFFSET page_offset;
$$;

INSERT INTO schema_migrations (version, checksum) VALUES ('011_service_modes_multi_selection.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 012_monetization_multi_businesses_and_subscriptions.sql >>>
-- Migration 012: Monetização, Multi-Negócios (Destrave de CPF/CNPJ) e Assinaturas Mercado Pago
-- Permite que uma mesma pessoa/dona tenha múltiplos negócios vinculados ao mesmo CPF/CNPJ.
-- Cria as tabelas de Planos, Assinaturas e Indicação (Ganhe 1 Mês Grátis).

-- 1. Destravar unicidade rígida de document_number para permitir múltiplos negócios da mesma dona
ALTER TABLE businesses DROP CONSTRAINT IF EXISTS businesses_document_number_key;
CREATE INDEX IF NOT EXISTS idx_businesses_document_number ON businesses(document_number);

-- Colunas de indicação em businesses
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS referral_code VARCHAR(50);
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS referred_by_code VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_businesses_referral_code ON businesses(referral_code);

-- 2. Tabela de Planos de Assinatura
CREATE TABLE IF NOT EXISTS plans (
  id VARCHAR(30) PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  price_cents INT NOT NULL,
  monthly_equivalent_cents INT NOT NULL,
  duration_months INT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inserir / Atualizar os 3 planos oficiais
INSERT INTO plans (id, name, price_cents, monthly_equivalent_cents, duration_months, is_active)
VALUES 
  ('mensal', 'Plano Mensal', 1500, 1500, 1, TRUE),
  ('semestral', 'Plano Semestral', 7794, 1299, 6, TRUE),
  ('anual', 'Plano Anual', 11988, 999, 12, TRUE)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  price_cents = EXCLUDED.price_cents,
  monthly_equivalent_cents = EXCLUDED.monthly_equivalent_cents,
  duration_months = EXCLUDED.duration_months;

-- 3. Tabela de Assinaturas (Vinculada à Dona / Usuário, com suporte futuro por negócio)
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  plan_id VARCHAR(30) REFERENCES plans(id),
  status VARCHAR(30) NOT NULL DEFAULT 'active', -- 'active', 'past_due', 'canceled'
  current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  current_period_end TIMESTAMPTZ NOT NULL,
  mp_payment_id VARCHAR(100),
  mp_preference_id VARCHAR(100),
  bonus_months_applied INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_owner ON subscriptions(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- 4. Tabela de Indicações (Member-Get-Member: Ganhe 1 Mês Grátis)
CREATE TABLE IF NOT EXISTS referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  referrer_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  referred_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  referred_business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  code VARCHAR(50) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending', -- 'pending', 'rewarded'
  reward_granted_days INT NOT NULL DEFAULT 30,
  rewarded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(code);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_user_id);

INSERT INTO schema_migrations (version, checksum) VALUES ('012_monetization_multi_businesses_and_subscriptions.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 013_sprint1_identity_and_curation.sql >>>
-- ==============================================================================
-- Migration 013: Sprint 1 - Identidade e Curadoria à Prova de Burla
-- Normalização de WhatsApp para E.164, flag owner_paused, flag de documento duplicado
-- e tabela de consentimentos LGPD persistidos.
-- ==============================================================================

-- 1. Coluna de WhatsApp normalizado em formato E.164 (+55...) com índice para busca exata
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_e164 VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp_e164 ON businesses(whatsapp_e164);

-- Backfill retroativo: normalizar números existentes
UPDATE businesses SET whatsapp_e164 = 
  CASE 
    WHEN regexp_replace(whatsapp, '\D', '', 'g') ~ '^55\d{10,11}$' THEN '+' || regexp_replace(whatsapp, '\D', '', 'g')
    WHEN length(regexp_replace(whatsapp, '\D', '', 'g')) IN (10, 11) THEN '+55' || regexp_replace(whatsapp, '\D', '', 'g')
    ELSE '+' || regexp_replace(whatsapp, '\D', '', 'g')
  END
WHERE whatsapp IS NOT NULL AND (whatsapp_e164 IS NULL OR whatsapp_e164 = '');

-- 2. Pausa do proprietário separada do status de moderação do administrador
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_paused BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_businesses_owner_paused ON businesses(owner_paused);

-- 3. Flag de detecção de documento (CNPJ/CPF) já vinculado a outro proprietário
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS document_flag_duplicate BOOLEAN NOT NULL DEFAULT FALSE;

-- 3.1 Coluna de rastreamento de uso de convite (T1.7)
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS used_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;

-- 4. Tabela de Consentimentos LGPD (Carta de Princípios, Termos e Privacidade)
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL, -- 'carta_principios', 'terms_of_service', 'privacy_policy'
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_hash VARCHAR(64),
    user_agent_hash VARCHAR(64),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consents_business_id ON consents(business_id);
CREATE INDEX IF NOT EXISTS idx_consents_user_id ON consents(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_type ON consents(type);

-- 5. Atualização da Política RLS de Busca Pública (T1.2 & T1.5)
-- Empresas pausadas pelo proprietário (owner_paused = TRUE) são omitidas da busca pública
ALTER TABLE consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE consents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_businesses_public_select ON businesses;
CREATE POLICY p_businesses_public_select ON businesses
  FOR SELECT USING (
    (status = 'approved' AND owner_paused = FALSE)
    OR current_setting('app.role', true) = 'admin'
    OR (
      current_setting('app.user_id', true) IS NOT NULL 
      AND current_setting('app.user_id', true) ~ '^[0-9a-fA-F-]{36}$'
      AND current_setting('app.user_id', true)::uuid = owner_user_id
    )
  );

DROP POLICY IF EXISTS p_consents_select ON consents;
CREATE POLICY p_consents_select ON consents
  FOR SELECT USING (
    current_setting('app.role', true) = 'admin'
    OR (
      current_setting('app.user_id', true) IS NOT NULL 
      AND current_setting('app.user_id', true) ~ '^[0-9a-fA-F-]{36}$'
      AND current_setting('app.user_id', true)::uuid = user_id
    )
  );

INSERT INTO schema_migrations (version, checksum) VALUES ('013_sprint1_identity_and_curation.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 014_sprint3_cities_and_spatial_indexing.sql >>>
-- ==============================================================================
-- Migration 014: Sprint 3 - Cidades, Índices Espaciais PostGIS e Lista de Espera (T3.1, T3.4)
-- ==============================================================================

-- 1. Tabela de Cidades com status de expansão (Cold Start / Rollout)
CREATE TABLE IF NOT EXISTS cities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    slug VARCHAR(120) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'soon', -- 'active' ou 'soon'
    location geography(POINT, 4326) NULL,
    interested_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cities_state_name ON cities(state, name);
CREATE INDEX IF NOT EXISTS idx_cities_slug ON cities(slug);
CREATE INDEX IF NOT EXISTS idx_cities_status ON cities(status);

-- 2. Tabela de Lista de Espera para Cidades 'soon'
CREATE TABLE IF NOT EXISTS city_waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    contact VARCHAR(100) NOT NULL,
    is_business BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_city_waitlist_city_id ON city_waitlist(city_id);

-- 3. Índices Espaciais GiST e Textuais GIN em businesses (T3.1)
CREATE INDEX IF NOT EXISTS idx_businesses_location_gist ON businesses USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_businesses_name_trgm ON businesses USING gin (name gin_trgm_ops);

-- 4. Coluna para sinalizar geocodificação pendente para curadoria manual (T3.2)
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS location_pending BOOLEAN NOT NULL DEFAULT FALSE;

-- 5. Seed de Cidades Iniciais (Polo Piloto Campinas e Região Ativa + Capitais em Expansão)
INSERT INTO cities (name, state, slug, status, location) VALUES
('Campinas', 'SP', 'sp-campinas', 'active', ST_SetSRID(ST_MakePoint(-47.0608, -22.9099), 4326)::geography),
('São Paulo', 'SP', 'sp-sao-paulo', 'active', ST_SetSRID(ST_MakePoint(-46.6333, -23.5505), 4326)::geography),
('Valinhos', 'SP', 'sp-valinhos', 'active', ST_SetSRID(ST_MakePoint(-46.9961, -22.9706), 4326)::geography),
('Vinhedo', 'SP', 'sp-vinhedo', 'active', ST_SetSRID(ST_MakePoint(-46.9744, -23.0297), 4326)::geography),
('Indaiatuba', 'SP', 'sp-indaiatuba', 'active', ST_SetSRID(ST_MakePoint(-47.2181, -23.0903), 4326)::geography),
('Americana', 'SP', 'sp-americana', 'active', ST_SetSRID(ST_MakePoint(-47.3314, -22.7378), 4326)::geography),
('Jundiaí', 'SP', 'sp-jundiai', 'active', ST_SetSRID(ST_MakePoint(-46.8842, -23.1857), 4326)::geography),
('Curitiba', 'PR', 'pr-curitiba', 'soon', ST_SetSRID(ST_MakePoint(-49.2731, -25.4284), 4326)::geography),
('Belo Horizonte', 'MG', 'mg-belo-horizonte', 'soon', ST_SetSRID(ST_MakePoint(-43.9378, -19.9208), 4326)::geography),
('Brasília', 'DF', 'df-brasilia', 'soon', ST_SetSRID(ST_MakePoint(-47.8825, -15.7942), 4326)::geography),
('Goiânia', 'GO', 'go-goiania', 'soon', ST_SetSRID(ST_MakePoint(-49.2648, -16.6869), 4326)::geography),
('Florianópolis', 'SC', 'sc-florianopolis', 'soon', ST_SetSRID(ST_MakePoint(-48.5496, -27.5954), 4326)::geography),
('Porto Alegre', 'RS', 'rs-porto-alegre', 'soon', ST_SetSRID(ST_MakePoint(-51.2177, -30.0346), 4326)::geography)
ON CONFLICT (slug) DO NOTHING;

-- 6. RLS em cities e city_waitlist
ALTER TABLE cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE city_waitlist ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_cities_select ON cities;
CREATE POLICY p_cities_select ON cities FOR SELECT USING (true);

DROP POLICY IF EXISTS p_city_waitlist_insert ON city_waitlist;
CREATE POLICY p_city_waitlist_insert ON city_waitlist FOR INSERT WITH CHECK (true);

INSERT INTO schema_migrations (version, checksum) VALUES ('014_sprint3_cities_and_spatial_indexing.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 015_sprint4_plans_and_payments.sql >>>
-- Migration 015: Sprint 4 - Monetização Consistente, Fonte Única de Planos e Idempotência de Pagamentos
-- T4.1: Tabela plans como fonte única da verdade com entitlements em centavos
-- T4.2: Entitlements de visibilidade e prioridade na busca
-- T4.3: Tabela payments para idempotência transacional estrita (ON CONFLICT DO NOTHING) contra webhooks duplicados

-- 1. Ampliar a tabela plans com colunas de entitlements e metadados
ALTER TABLE plans ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS badge VARCHAR(100);
ALTER TABLE plans ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS search_priority INT NOT NULL DEFAULT 1;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_categories INT NOT NULL DEFAULT 1;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_photos INT NOT NULL DEFAULT 3;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS has_leads_access BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS has_metrics_access BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS has_banner_access BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 2. Atualizar/Inserir os 3 planos oficiais com todos os entitlements e benefícios definidos
INSERT INTO plans (
  id, name, price_cents, monthly_equivalent_cents, duration_months,
  description, badge, is_featured, search_priority, max_categories, max_photos,
  has_leads_access, has_metrics_access, has_banner_access, is_active
) VALUES
  (
    'mensal', 'Plano Mensal', 1500, 1500, 1,
    'Flexibilidade total, sem fidelidade. Cancele quando quiser.',
    'Sem Fidelidade', FALSE, 10, 3, 10,
    TRUE, TRUE, FALSE, TRUE
  ),
  (
    'semestral', 'Plano Semestral', 7794, 1299, 6,
    '6 meses garantidos de visibilidade na sua região com 13% de economia.',
    'Economize 13%', FALSE, 20, 5, 15,
    TRUE, TRUE, FALSE, TRUE
  ),
  (
    'anual', 'Plano Anual', 11988, 999, 12,
    'O mais escolhido pelos empresários patriotas: menos de R$ 0,33 por dia (em até 12x de R$ 9,99).',
    'Mais Popular • 33% OFF', TRUE, 30, 10, 20,
    TRUE, TRUE, TRUE, TRUE
  )
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  price_cents = EXCLUDED.price_cents,
  monthly_equivalent_cents = EXCLUDED.monthly_equivalent_cents,
  duration_months = EXCLUDED.duration_months,
  description = EXCLUDED.description,
  badge = EXCLUDED.badge,
  is_featured = EXCLUDED.is_featured,
  search_priority = EXCLUDED.search_priority,
  max_categories = EXCLUDED.max_categories,
  max_photos = EXCLUDED.max_photos,
  has_leads_access = EXCLUDED.has_leads_access,
  has_metrics_access = EXCLUDED.has_metrics_access,
  has_banner_access = EXCLUDED.has_banner_access,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

-- 3. Tabela de Pagamentos com chave única mp_payment_id para garantir idempotência transacional
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mp_payment_id VARCHAR(100) NOT NULL UNIQUE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  plan_id VARCHAR(30) REFERENCES plans(id),
  amount_cents INT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'BRL',
  status VARCHAR(50) NOT NULL, -- 'approved', 'refunded', 'charged_back', 'pending', 'rejected', 'cancelled'
  raw_payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_mp_payment_id ON payments(mp_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- 4. Otimização de busca e expiração em subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_owner_status ON subscriptions(owner_user_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_period_end ON subscriptions(current_period_end);

INSERT INTO schema_migrations (version, checksum) VALUES ('015_sprint4_plans_and_payments.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 016_sprint5_whatsapp_and_leads.sql >>>
-- Migration 016: Sprint 5 - WhatsApp Oficial Híbrido, Bot de Orçamentos e Leads
-- T5.1: Deduplicação de eventos (wa_events) e registro de opt-in/opt-out (wa_optins)
-- T5.3: Tabelas de intermediação de pedidos de orçamento: leads e lead_offers
-- T5.4: Avaliações verificadas (lead_reviews) atreladas exclusivamente a pedidos reais concluídos

-- 1. Deduplicação e Auditoria de Eventos de Mensagens
CREATE TABLE IF NOT EXISTS wa_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider VARCHAR(30) NOT NULL, -- 'meta_cloud', 'evolution'
  event_id VARCHAR(150) NOT NULL UNIQUE,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wa_events_event_id ON wa_events(event_id);

-- 2. Controle de Opt-In e Opt-Out (LGPD e Conformidade com Meta)
CREATE TABLE IF NOT EXISTS wa_optins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_e164 VARCHAR(30) NOT NULL,
  scope VARCHAR(50) NOT NULL DEFAULT 'all', -- 'auth', 'utility', 'marketing', 'all'
  status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'revoked'
  origin VARCHAR(50) DEFAULT 'whatsapp',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_wa_optins_phone_status ON wa_optins(phone_e164, status);

-- 3. Pedidos de Orçamento Intermediados (Leads)
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_phone_e164 VARCHAR(30) NOT NULL,
  client_name VARCHAR(100),
  category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
  description TEXT NOT NULL,
  urgency VARCHAR(30) DEFAULT 'normal', -- 'urgent', 'normal', 'budget'
  location GEOGRAPHY(Point, 4326),
  city VARCHAR(100),
  state VARCHAR(2),
  status VARCHAR(30) NOT NULL DEFAULT 'pending_offers', -- 'pending_offers', 'matched', 'expired', 'canceled'
  matched_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_category ON leads(category_id);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);

-- 4. Ofertas de Leads Enviadas aos Lojistas (SLA e Concorrência Justa)
CREATE TABLE IF NOT EXISTS lead_offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  offer_code VARCHAR(20) NOT NULL, -- Código curto para resposta em texto na Evolution ou botões Meta
  status VARCHAR(30) NOT NULL DEFAULT 'sent', -- 'sent', 'accepted', 'declined', 'expired'
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  responded_at TIMESTAMPTZ,
  response_seconds INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_offers_lead ON lead_offers(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_offers_business ON lead_offers(business_id);
CREATE INDEX IF NOT EXISTS idx_lead_offers_code ON lead_offers(offer_code);

-- 5. Avaliações Verificadas (Somente clientes com pedidos reais atendidos)
CREATE TABLE IF NOT EXISTS lead_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment TEXT,
  status VARCHAR(30) NOT NULL DEFAULT 'approved', -- 'pending_moderation', 'approved', 'rejected'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_reviews_biz ON lead_reviews(business_id);

INSERT INTO schema_migrations (version, checksum) VALUES ('016_sprint5_whatsapp_and_leads.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 017_sprint7_business_network_and_endorsements.sql >>>
-- ==============================================================================
-- Migração 017: Sprint 7 - Rede de Negócios Confiáveis e Endosso Entre Pares
-- Objetivo: Fortalecer a comunidade com indicações mútuas, disponibilidade imediata
--           e reputação coletiva, sem leilão de menor preço.
-- ==============================================================================

-- 1. Campos de Disponibilidade Imediata e Rede em 'businesses'
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS availability_until TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS network_badge VARCHAR(50) NOT NULL DEFAULT 'membro_verificado',
ADD COLUMN IF NOT EXISTS endorsements_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_businesses_availability ON businesses(availability_until) 
WHERE availability_until IS NOT NULL;

-- 2. Tabela de Endossos e Recomendações Mútuas entre Empresas Parceiras
CREATE TABLE IF NOT EXISTS peer_endorsements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endorsing_business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    endorsed_business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL DEFAULT 'peer' 
        CHECK (relationship_type IN ('client', 'partner', 'peer', 'supplier')),
    testimonial VARCHAR(500) NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_no_self_endorsement CHECK (endorsing_business_id != endorsed_business_id),
    CONSTRAINT uq_peer_endorsement UNIQUE (endorsing_business_id, endorsed_business_id)
);

CREATE INDEX IF NOT EXISTS idx_peer_endorsements_endorsed ON peer_endorsements(endorsed_business_id);
CREATE INDEX IF NOT EXISTS idx_peer_endorsements_endorsing ON peer_endorsements(endorsing_business_id);

-- 3. Habilitar RLS
ALTER TABLE peer_endorsements ENABLE ROW LEVEL SECURITY;

-- Política de Leitura Pública: apenas endossos públicos onde ambas as empresas estão aprovadas
DROP POLICY IF EXISTS peer_endorsements_public_read ON peer_endorsements;
CREATE POLICY peer_endorsements_public_read ON peer_endorsements
    FOR SELECT
    USING (
        is_public = TRUE
        AND EXISTS (
            SELECT 1 FROM businesses b1 
            WHERE b1.id = peer_endorsements.endorsed_business_id 
              AND b1.status = 'approved' 
              AND b1.owner_paused = FALSE
        )
        AND EXISTS (
            SELECT 1 FROM businesses b2 
            WHERE b2.id = peer_endorsements.endorsing_business_id 
              AND b2.status = 'approved'
        )
    );

-- Política de Modificação: apenas a aplicação / dono autenticado
DROP POLICY IF EXISTS peer_endorsements_app_write ON peer_endorsements;
CREATE POLICY peer_endorsements_app_write ON peer_endorsements
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');

-- 4. Função e Trigger para atualizar contador 'endorsements_count' automaticamente
CREATE OR REPLACE FUNCTION update_endorsements_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = NEW.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = NEW.endorsed_business_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = OLD.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = OLD.endorsed_business_id;
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = NEW.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = NEW.endorsed_business_id;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_endorsements_count ON peer_endorsements;
CREATE TRIGGER trg_update_endorsements_count
AFTER INSERT OR UPDATE OR DELETE ON peer_endorsements
FOR EACH ROW EXECUTE FUNCTION update_endorsements_count();

INSERT INTO schema_migrations (version, checksum) VALUES ('017_sprint7_business_network_and_endorsements.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 018_job_openings_module.sql >>>
-- ==============================================================================
-- Migração 018: Módulo de Vagas de Emprego (v1)
-- Objetivo: Permitir que empresas aprovadas sinalizem vagas abertas, com moderação
--           automática, blindagem jurídica (sem dados sensíveis) e limite de 3 vagas.
-- ==============================================================================

-- 1. Tipos Enumerados do Módulo de Vagas
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM ('pending_review', 'active', 'expired', 'closed', 'rejected');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_contract_type') THEN
        CREATE TYPE job_contract_type AS ENUM ('clt', 'temporario', 'meio_periodo', 'estagio', 'aprendiz', 'autonomo');
    END IF;
END $$;

-- 2. Tabela Principal de Vagas de Emprego
CREATE TABLE IF NOT EXISTS job_openings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    title VARCHAR(60) NOT NULL,
    title_normalized VARCHAR(60) NOT NULL,
    description VARCHAR(280),
    contract_type job_contract_type NOT NULL,
    openings_count SMALLINT NOT NULL DEFAULT 1 CHECK (openings_count BETWEEN 1 AND 20),
    status job_status NOT NULL DEFAULT 'pending_review',
    owner_paused BOOLEAN NOT NULL DEFAULT FALSE,
    admin_hold BOOLEAN NOT NULL DEFAULT FALSE,
    moderation_flags TEXT[] NOT NULL DEFAULT '{}',
    rejection_code VARCHAR(40),
    published_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    renewed_count SMALLINT NOT NULL DEFAULT 0 CHECK (renewed_count <= 2),
    close_reason VARCHAR(30),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices otimizados
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_business_title
    ON job_openings (business_id, title_normalized)
    WHERE status IN ('pending_review', 'active');

CREATE INDEX IF NOT EXISTS idx_jobs_public
    ON job_openings (published_at DESC)
    WHERE status = 'active' AND NOT owner_paused AND NOT admin_hold;

CREATE INDEX IF NOT EXISTS idx_jobs_business ON job_openings (business_id);
CREATE INDEX IF NOT EXISTS idx_jobs_expiry ON job_openings (expires_at) WHERE status = 'active';

-- 3. Limite de 3 vagas abertas por empresa (com trava de concorrência por advisory lock)
CREATE OR REPLACE FUNCTION jobs_enforce_limit() RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext(NEW.business_id::text));
    IF NEW.status IN ('pending_review', 'active') AND (
        SELECT count(*) FROM job_openings
         WHERE business_id = NEW.business_id
           AND status IN ('pending_review', 'active')
           AND id <> NEW.id) >= 3 THEN
        RAISE EXCEPTION 'JOB_LIMIT_REACHED' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_jobs_limit ON job_openings;
CREATE TRIGGER trg_jobs_limit BEFORE INSERT OR UPDATE OF status ON job_openings
    FOR EACH ROW EXECUTE FUNCTION jobs_enforce_limit();

-- 4. Log de Auditoria Permanente de Decisões de Vagas (Append-only)
CREATE TABLE IF NOT EXISTS job_review_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES job_openings(id) ON DELETE CASCADE,
    actor VARCHAR(10) NOT NULL,
    actor_id UUID,
    action VARCHAR(30) NOT NULL,
    from_status job_status,
    to_status job_status,
    reason_code VARCHAR(40),
    flags TEXT[],
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_review_log_job ON job_review_log(job_id);

-- 5. Denúncias de Vagas (IP em hash SHA-256 com deduplicação diária)
CREATE TABLE IF NOT EXISTS job_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES job_openings(id) ON DELETE CASCADE,
    reason VARCHAR(20) NOT NULL,
    details VARCHAR(200),
    ip_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_job_report_daily
    ON job_reports (job_id, ip_hash, (created_at::date));

-- 6. Termos de Moderação de Conteúdo
CREATE TABLE IF NOT EXISTS moderation_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_normalized VARCHAR(80) NOT NULL UNIQUE,
    category VARCHAR(20) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    match_type VARCHAR(10) NOT NULL DEFAULT 'phrase',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed de Termos Iniciais Monitorados
INSERT INTO moderation_terms (term_normalized, category, severity, match_type)
VALUES
    -- Discriminação
    ('boa aparencia', 'discriminacao', 'block', 'phrase'),
    ('aparencia', 'discriminacao', 'block', 'word'),
    ('foto obrigatoria', 'discriminacao', 'block', 'phrase'),
    ('apenas mulheres', 'discriminacao', 'block', 'phrase'),
    ('apenas homens', 'discriminacao', 'block', 'phrase'),
    ('somente feminino', 'discriminacao', 'block', 'phrase'),
    ('somente masculino', 'discriminacao', 'block', 'phrase'),
    ('solteiro', 'discriminacao', 'block', 'word'),
    ('casado', 'discriminacao', 'block', 'word'),
    ('sem filhos', 'discriminacao', 'block', 'phrase'),
    ('ate 25 anos', 'discriminacao', 'block', 'phrase'),
    ('idade entre', 'discriminacao', 'block', 'phrase'),
    -- Convicção Política / Religiosa
    ('de direita', 'conviccao', 'block', 'phrase'),
    ('de esquerda', 'conviccao', 'block', 'phrase'),
    ('alinhado politicamente', 'conviccao', 'block', 'phrase'),
    ('partido', 'conviccao', 'block', 'word'),
    ('cristao', 'conviccao', 'block', 'word'),
    ('evangelico', 'conviccao', 'block', 'word'),
    ('catolico', 'conviccao', 'block', 'word'),
    ('ateu', 'conviccao', 'block', 'word'),
    -- Golpe / Cobrança
    ('taxa de inscricao', 'golpe', 'block', 'phrase'),
    ('deposito adiantado', 'golpe', 'block', 'phrase'),
    ('pagamento adiantado', 'golpe', 'block', 'phrase'),
    ('renda extra garantida', 'golpe', 'block', 'phrase'),
    ('trabalhe de casa ganhando', 'golpe', 'block', 'phrase'),
    ('multinivel', 'golpe', 'block', 'word'),
    ('ganhe dinheiro facil', 'golpe', 'block', 'phrase'),
    -- Revisão humana recomendada
    ('disponibilidade total', 'review', 'review', 'phrase'),
    ('boa presenca', 'review', 'review', 'phrase'),
    ('perfil agressivo', 'review', 'review', 'phrase')
ON CONFLICT (term_normalized) DO NOTHING;

-- 7. Integração de Métricas de Candidatura em 'contact_events'
ALTER TABLE contact_events ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES job_openings(id) ON DELETE SET NULL;

-- 8. Configuração de Row Level Security (RLS)
ALTER TABLE job_openings ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_reports ENABLE ROW LEVEL SECURITY;

-- Leitura pública de vagas: somente vagas ativas, não pausadas pelo dono, sem hold do admin,
-- dentro do prazo de validade e com a empresa aprovada e ativa.
DROP POLICY IF EXISTS p_jobs_public_read ON job_openings;
CREATE POLICY p_jobs_public_read ON job_openings
    FOR SELECT
    USING (
        status = 'active'
        AND NOT owner_paused
        AND NOT admin_hold
        AND expires_at > NOW()
        AND EXISTS (
            SELECT 1 FROM businesses b
             WHERE b.id = job_openings.business_id
               AND b.status = 'approved'
               AND NOT b.owner_paused
        )
    );

-- Acesso da aplicação e administração
DROP POLICY IF EXISTS p_jobs_app_all ON job_openings;
CREATE POLICY p_jobs_app_all ON job_openings
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');

DROP POLICY IF EXISTS p_job_reports_app_all ON job_reports;
CREATE POLICY p_job_reports_app_all ON job_reports
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');

INSERT INTO schema_migrations (version, checksum) VALUES ('018_job_openings_module.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> MIGRAÇÃO: 019_update_monthly_plan_price.sql >>>
-- ==============================================================================
-- Migration 019: Update Monthly Plan Price
-- Description: Ajusta o valor do plano mensal de R$ 15,00 para R$ 14,90 (1490 centavos).
-- ==============================================================================

UPDATE plans
SET 
  price_cents = 1490,
  monthly_equivalent_cents = 1490,
  updated_at = NOW()
WHERE id = 'mensal';

INSERT INTO schema_migrations (version, checksum) VALUES ('019_update_monthly_plan_price.sql', 'manual_reset') ON CONFLICT DO NOTHING;

-- >>> SEED: categories.sql >>>
-- ==============================================================================
-- Seed: Curated Categories
-- ==============================================================================
\i ../migrations/004_seed_categories.sql



-- >>> SEED: sample_businesses_campinas.sql >>>
-- ==============================================================================
-- Seed: Sample Pilot Businesses (Campinas - SP)
-- Description: Realistic seed data for testing proximity search,
--              service radius (at_customer), and triage states.
-- NOTE: Administradores DEVEM ser provisionados via script backend.scripts.create_admin
-- ==============================================================================

-- 1. Empresas Piloto em Campinas-SP
-- Coordenadas de referência no centro de Campinas: Lat -22.9056, Lng -47.0608

-- Empresa 1: Eletricista Residencial (at_customer com raio de 25km)
INSERT INTO businesses (
  id, name, slug, description, listing_type, document_type, document_number,
  cnpj_situation, whatsapp, phone, street, number, neighborhood, city, state, postal_code,
  show_full_address, location, service_mode, service_radius_km,
  status, source, is_verified
) VALUES (
  'b0000000-0000-0000-0000-000000000001',
  'Silva Instalações e Eletricista 24h',
  'silva-instalacoes-eletricista-campinas',
  'Especialista em reformas elétricas, troca de disjuntores, quadros de distribuição e padrões CPFL. Atendimento rápido e laudo técnico.',
  'service', 'CNPJ', '12345678000195', 'ATIVA',
  '5519987654321', '1932345678',
  'Rua Barão de Jaguara', '1120', 'Centro', 'Campinas', 'SP', '13015002',
  false,
  ST_SetSRID(ST_MakePoint(-47.0592, -22.9064), 4326)::geography,
  'at_customer', 25,
  'approved', 'seeded', true
) ON CONFLICT (slug) DO NOTHING;

-- Empresa 2: Padaria e Confeitaria Artesanal (at_location + delivery)
INSERT INTO businesses (
  id, name, slug, description, listing_type, document_type, document_number,
  cnpj_situation, whatsapp, phone, street, number, neighborhood, city, state, postal_code,
  show_full_address, location, service_mode, service_radius_km,
  status, source, is_verified
) VALUES (
  'b0000000-0000-0000-0000-000000000002',
  'Padaria Pão Dourado Cambuí',
  'padaria-pao-dourado-cambui',
  'Pães de fermentação natural, bolos caseiros, café especial e café da manhã colonial. Encomendas para eventos e consumo no local.',
  'both', 'CNPJ', '98765432000110', 'ATIVA',
  '5519991234567', '1932519988',
  'Rua Coronel Quirino', '850', 'Cambuí', 'Campinas', 'SP', '13025001',
  true,
  ST_SetSRID(ST_MakePoint(-47.0515, -22.8985), 4326)::geography,
  'both', 8,
  'approved', 'seeded', true
) ON CONFLICT (slug) DO NOTHING;

-- Empresa 3: Ar-Condicionado & Climatização (at_customer, 35km)
INSERT INTO businesses (
  id, name, slug, description, listing_type, document_type, document_number,
  cnpj_situation, whatsapp, phone, street, number, neighborhood, city, state, postal_code,
  show_full_address, location, service_mode, service_radius_km,
  status, source, is_verified
) VALUES (
  'b0000000-0000-0000-0000-000000000003',
  'ClimaTop Ar-Condicionado',
  'climatop-ar-condicionado-campinas',
  'Instalação, higienização química com laudo PMOC e manutenção preventiva e corretiva de ar-condicionado split, inverter e cassete.',
  'service', 'CNPJ', '45678912000133', 'ATIVA',
  '5519977889900', '1933012233',
  'Avenida Brasil', '1400', 'Guanabara', 'Campinas', 'SP', '13073010',
  false,
  ST_SetSRID(ST_MakePoint(-47.0700, -22.8890), 4326)::geography,
  'at_customer', 35,
  'approved', 'seeded', true
) ON CONFLICT (slug) DO NOTHING;

-- Empresa 4: Empresa em análise (pending_review) para testar a fila de triagem
INSERT INTO businesses (
  id, name, slug, description, listing_type, document_type, document_number,
  cnpj_situation, whatsapp, phone, street, number, neighborhood, city, state, postal_code,
  show_full_address, location, service_mode, service_radius_km,
  status, source, is_verified
) VALUES (
  'b0000000-0000-0000-0000-000000000004',
  'Marcenaria Nobre Design',
  'marcenaria-nobre-design-campinas',
  'Móveis sob medida para cozinhas, dormitórios e escritórios comerciais com MDF de alta densidade.',
  'service', 'CNPJ', '33445566000177', 'ATIVA',
  '5519988112233', '1932998877',
  'Rua Doutor Buarque de Macedo', '300', 'Vila Nova', 'Campinas', 'SP', '13073050',
  true,
  ST_SetSRID(ST_MakePoint(-47.0735, -22.8830), 4326)::geography,
  'both', 20,
  'pending_review', 'application', false
) ON CONFLICT (slug) DO NOTHING;

-- Vínculo das categorias
INSERT INTO business_categories (business_id, category_id, is_primary)
SELECT 'b0000000-0000-0000-0000-000000000001', id, true
FROM categories WHERE slug = 'eletricista'
ON CONFLICT DO NOTHING;

INSERT INTO business_categories (business_id, category_id, is_primary)
SELECT 'b0000000-0000-0000-0000-000000000002', id, true
FROM categories WHERE slug = 'padaria-confeitaria'
ON CONFLICT DO NOTHING;

INSERT INTO business_categories (business_id, category_id, is_primary)
SELECT 'b0000000-0000-0000-0000-000000000003', id, true
FROM categories WHERE slug = 'ar-condicionado-climatizacao'
ON CONFLICT DO NOTHING;

INSERT INTO business_categories (business_id, category_id, is_primary)
SELECT 'b0000000-0000-0000-0000-000000000004', id, true
FROM categories WHERE slug = 'marcenaria'
ON CONFLICT DO NOTHING;


