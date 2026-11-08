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
