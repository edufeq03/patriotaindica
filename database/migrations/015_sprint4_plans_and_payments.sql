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
