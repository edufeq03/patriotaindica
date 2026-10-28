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
