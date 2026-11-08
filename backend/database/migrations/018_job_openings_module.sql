-- ==============================================================================
-- Migração 018: Módulo de Vagas de Emprego (v1)
-- Objetivo: Permitir que empresas aprovadas sinalizem vagas abertas, com moderação
--           automática, blindagem jurídica (sem dados sensíveis) e limite de 3 vagas.
-- ==============================================================================

-- 1. Tipos Enumerados do Módulo de Vagas
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM ('pending_review', 'active', 'expired', 'closed', 'rejected');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_contract_type') THEN
        CREATE TYPE job_contract_type AS ENUM ('clt', 'temporario', 'meio_periodo', 'estagio', 'aprendiz', 'autonomo');
    END IF;
END $$;

-- 2. Tabela Principal de Vagas de Emprego
CREATE TABLE IF NOT EXISTS job_openings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    title VARCHAR(60) NOT NULL,
    title_normalized VARCHAR(60) NOT NULL,
    description VARCHAR(280),
    contract_type job_contract_type NOT NULL,
    openings_count SMALLINT NOT NULL DEFAULT 1 CHECK (openings_count BETWEEN 1 AND 20),
    status job_status NOT NULL DEFAULT 'pending_review',
    owner_paused BOOLEAN NOT NULL DEFAULT FALSE,
    admin_hold BOOLEAN NOT NULL DEFAULT FALSE,
    moderation_flags TEXT[] NOT NULL DEFAULT '{}',
    rejection_code VARCHAR(40),
    published_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    renewed_count SMALLINT NOT NULL DEFAULT 0 CHECK (renewed_count <= 2),
    close_reason VARCHAR(30),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices otimizados
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_business_title
    ON job_openings (business_id, title_normalized)
    WHERE status IN ('pending_review', 'active');

CREATE INDEX IF NOT EXISTS idx_jobs_public
    ON job_openings (published_at DESC)
    WHERE status = 'active' AND NOT owner_paused AND NOT admin_hold;

CREATE INDEX IF NOT EXISTS idx_jobs_business ON job_openings (business_id);
CREATE INDEX IF NOT EXISTS idx_jobs_expiry ON job_openings (expires_at) WHERE status = 'active';

-- 3. Limite de 3 vagas abertas por empresa (com trava de concorrência por advisory lock)
CREATE OR REPLACE FUNCTION jobs_enforce_limit() RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext(NEW.business_id::text));
    IF NEW.status IN ('pending_review', 'active') AND (
        SELECT count(*) FROM job_openings
         WHERE business_id = NEW.business_id
           AND status IN ('pending_review', 'active')
           AND id <> NEW.id) >= 3 THEN
        RAISE EXCEPTION 'JOB_LIMIT_REACHED' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_jobs_limit ON job_openings;
CREATE TRIGGER trg_jobs_limit BEFORE INSERT OR UPDATE OF status ON job_openings
    FOR EACH ROW EXECUTE FUNCTION jobs_enforce_limit();

-- 4. Log de Auditoria Permanente de Decisões de Vagas (Append-only)
CREATE TABLE IF NOT EXISTS job_review_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES job_openings(id) ON DELETE CASCADE,
    actor VARCHAR(10) NOT NULL,
    actor_id UUID,
    action VARCHAR(30) NOT NULL,
    from_status job_status,
    to_status job_status,
    reason_code VARCHAR(40),
    flags TEXT[],
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_review_log_job ON job_review_log(job_id);

-- 5. Denúncias de Vagas (IP em hash SHA-256 com deduplicação diária)
CREATE TABLE IF NOT EXISTS job_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES job_openings(id) ON DELETE CASCADE,
    reason VARCHAR(20) NOT NULL,
    details VARCHAR(200),
    ip_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_job_report_daily
    ON job_reports (job_id, ip_hash, (created_at::date));

-- 6. Termos de Moderação de Conteúdo
CREATE TABLE IF NOT EXISTS moderation_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_normalized VARCHAR(80) NOT NULL UNIQUE,
    category VARCHAR(20) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    match_type VARCHAR(10) NOT NULL DEFAULT 'phrase',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed de Termos Iniciais Monitorados
INSERT INTO moderation_terms (term_normalized, category, severity, match_type)
VALUES
    -- Discriminação
    ('boa aparencia', 'discriminacao', 'block', 'phrase'),
    ('aparencia', 'discriminacao', 'block', 'word'),
    ('foto obrigatoria', 'discriminacao', 'block', 'phrase'),
    ('apenas mulheres', 'discriminacao', 'block', 'phrase'),
    ('apenas homens', 'discriminacao', 'block', 'phrase'),
    ('somente feminino', 'discriminacao', 'block', 'phrase'),
    ('somente masculino', 'discriminacao', 'block', 'phrase'),
    ('solteiro', 'discriminacao', 'block', 'word'),
    ('casado', 'discriminacao', 'block', 'word'),
    ('sem filhos', 'discriminacao', 'block', 'phrase'),
    ('ate 25 anos', 'discriminacao', 'block', 'phrase'),
    ('idade entre', 'discriminacao', 'block', 'phrase'),
    -- Convicção Política / Religiosa
    ('de direita', 'conviccao', 'block', 'phrase'),
    ('de esquerda', 'conviccao', 'block', 'phrase'),
    ('alinhado politicamente', 'conviccao', 'block', 'phrase'),
    ('partido', 'conviccao', 'block', 'word'),
    ('cristao', 'conviccao', 'block', 'word'),
    ('evangelico', 'conviccao', 'block', 'word'),
    ('catolico', 'conviccao', 'block', 'word'),
    ('ateu', 'conviccao', 'block', 'word'),
    -- Golpe / Cobrança
    ('taxa de inscricao', 'golpe', 'block', 'phrase'),
    ('deposito adiantado', 'golpe', 'block', 'phrase'),
    ('pagamento adiantado', 'golpe', 'block', 'phrase'),
    ('renda extra garantida', 'golpe', 'block', 'phrase'),
    ('trabalhe de casa ganhando', 'golpe', 'block', 'phrase'),
    ('multinivel', 'golpe', 'block', 'word'),
    ('ganhe dinheiro facil', 'golpe', 'block', 'phrase'),
    -- Revisão humana recomendada
    ('disponibilidade total', 'review', 'review', 'phrase'),
    ('boa presenca', 'review', 'review', 'phrase'),
    ('perfil agressivo', 'review', 'review', 'phrase')
ON CONFLICT (term_normalized) DO NOTHING;

-- 7. Integração de Métricas de Candidatura em 'contact_events'
ALTER TABLE contact_events ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES job_openings(id) ON DELETE SET NULL;

-- 8. Configuração de Row Level Security (RLS)
ALTER TABLE job_openings ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_reports ENABLE ROW LEVEL SECURITY;

-- Leitura pública de vagas: somente vagas ativas, não pausadas pelo dono, sem hold do admin,
-- dentro do prazo de validade e com a empresa aprovada e ativa.
DROP POLICY IF EXISTS p_jobs_public_read ON job_openings;
CREATE POLICY p_jobs_public_read ON job_openings
    FOR SELECT
    USING (
        status = 'active'
        AND NOT owner_paused
        AND NOT admin_hold
        AND expires_at > NOW()
        AND EXISTS (
            SELECT 1 FROM businesses b
             WHERE b.id = job_openings.business_id
               AND b.status = 'approved'
               AND NOT b.owner_paused
        )
    );

-- Acesso da aplicação e administração
DROP POLICY IF EXISTS p_jobs_app_all ON job_openings;
CREATE POLICY p_jobs_app_all ON job_openings
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');

DROP POLICY IF EXISTS p_job_reports_app_all ON job_reports;
CREATE POLICY p_job_reports_app_all ON job_reports
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');
