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
