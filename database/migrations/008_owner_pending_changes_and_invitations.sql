-- ==============================================================================
-- Migration 008: Owner Pending Changes and Secure Token Invitations
-- Description:
-- 1. [H3] business_pending_changes: dono propõe alterações em campos de risco
--    sem despublicar a versão aprovada e sem bypass de triagem.
-- 2. [M12] invitations: convites criptográficos baseados em SHA-256 (sem tokens em texto claro).
-- ==============================================================================

-- 1. Tabela de Alterações Pendentes do Dono (H3)
CREATE TABLE IF NOT EXISTS business_pending_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  proposed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  changes JSONB NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending_review',
  reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  rejection_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_changes_business ON business_pending_changes(business_id);
CREATE INDEX IF NOT EXISTS idx_pending_changes_status ON business_pending_changes(status);

-- 2. Tabela de Convites Seguros (M12)
CREATE TABLE IF NOT EXISTS invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID REFERENCES businesses(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  phone VARCHAR(20),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_token_hash ON invitations(token_hash);
CREATE INDEX IF NOT EXISTS idx_invitations_business ON invitations(business_id);
