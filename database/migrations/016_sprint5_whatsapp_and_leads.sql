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
