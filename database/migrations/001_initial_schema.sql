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
