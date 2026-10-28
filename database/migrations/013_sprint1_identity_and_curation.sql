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
