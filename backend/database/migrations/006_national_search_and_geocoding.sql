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
