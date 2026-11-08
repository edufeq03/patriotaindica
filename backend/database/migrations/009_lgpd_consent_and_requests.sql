-- Migration 009: Registro de solicitacoes de privacidade e direitos do titular (LGPD M11)
CREATE TABLE IF NOT EXISTS data_subject_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(32) NOT NULL, -- 'deletion', 'revocation', 'export', 'correction', 'information'
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(32),
    details TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'received', -- 'received', 'processing', 'completed', 'rejected'
    ip_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_data_subject_requests_email ON data_subject_requests(email);
CREATE INDEX IF NOT EXISTS idx_data_subject_requests_status ON data_subject_requests(status);
