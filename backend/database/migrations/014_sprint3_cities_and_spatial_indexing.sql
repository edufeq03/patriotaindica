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
