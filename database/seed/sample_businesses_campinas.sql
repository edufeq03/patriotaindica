-- ==============================================================================
-- Seed: Sample Pilot Businesses (Campinas - SP)
-- Description: Realistic seed data for testing proximity search,
--              service radius (at_customer), and triage states.
-- ==============================================================================

-- 1. Usuário Administrador Inicial (senha demo: admin123)
-- Hash bcrypt para 'admin123'
INSERT INTO users (id, name, email, password_hash, role)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'Administrador Curadoria',
  'admin@mktdireita.com.br',
  '$2b$12$e8YQZ0c1UaY5K7XzVl7tqu1N3eEsqtWnCUG5z5tKj2oQc1Wq3dZae',
  'admin'
) ON CONFLICT (email) DO NOTHING;

-- 2. Empresas Piloto em Campinas-SP
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
