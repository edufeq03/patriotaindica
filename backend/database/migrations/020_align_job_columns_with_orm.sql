-- ==============================================================================
-- Migration 020: Alinha colunas do Módulo de Vagas com o ORM (SQLAlchemy)
-- Problema: a 018 criou status/contract_type como ENUM e flags como TEXT[],
--           mas o ORM envia VARCHAR e JSONB -> INSERT falhava com erro 500.
-- Solução: VARCHAR + CHECK (mesmas regras de domínio) e JSONB.
-- ==============================================================================

-- 1. Remover objetos que dependem do tipo das colunas
DROP POLICY IF EXISTS p_jobs_public_read ON job_openings;
DROP INDEX IF EXISTS uq_job_business_title;
DROP INDEX IF EXISTS idx_jobs_public;
DROP INDEX IF EXISTS idx_jobs_expiry;
DROP TRIGGER IF EXISTS trg_jobs_limit ON job_openings;

-- 2. job_openings: status / contract_type -> VARCHAR; moderation_flags -> JSONB
ALTER TABLE job_openings ALTER COLUMN status DROP DEFAULT;
ALTER TABLE job_openings ALTER COLUMN status TYPE VARCHAR(20) USING status::text;
ALTER TABLE job_openings ALTER COLUMN status SET DEFAULT 'pending_review';

ALTER TABLE job_openings ALTER COLUMN contract_type TYPE VARCHAR(30) USING contract_type::text;

ALTER TABLE job_openings ALTER COLUMN moderation_flags DROP DEFAULT;
ALTER TABLE job_openings ALTER COLUMN moderation_flags TYPE JSONB USING to_jsonb(moderation_flags);
ALTER TABLE job_openings ALTER COLUMN moderation_flags SET DEFAULT '[]'::jsonb;

ALTER TABLE job_openings DROP CONSTRAINT IF EXISTS ck_job_status;
ALTER TABLE job_openings ADD CONSTRAINT ck_job_status
    CHECK (status IN ('pending_review', 'active', 'expired', 'closed', 'rejected'));

ALTER TABLE job_openings DROP CONSTRAINT IF EXISTS ck_job_contract_type;
ALTER TABLE job_openings ADD CONSTRAINT ck_job_contract_type
    CHECK (contract_type IN ('clt', 'temporario', 'meio_periodo', 'estagio', 'aprendiz', 'autonomo'));

-- 3. job_review_log: from_status / to_status -> VARCHAR; flags -> JSONB
ALTER TABLE job_review_log ALTER COLUMN from_status TYPE VARCHAR(20) USING from_status::text;
ALTER TABLE job_review_log ALTER COLUMN to_status TYPE VARCHAR(20) USING to_status::text;
ALTER TABLE job_review_log ALTER COLUMN flags TYPE JSONB USING to_jsonb(flags);

-- 4. Recriar índices
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_business_title
    ON job_openings (business_id, title_normalized)
    WHERE status IN ('pending_review', 'active');

CREATE INDEX IF NOT EXISTS idx_jobs_public
    ON job_openings (published_at DESC)
    WHERE status = 'active' AND NOT owner_paused AND NOT admin_hold;

CREATE INDEX IF NOT EXISTS idx_jobs_expiry ON job_openings (expires_at) WHERE status = 'active';

-- 5. Recriar trigger de limite de 3 vagas
CREATE TRIGGER trg_jobs_limit BEFORE INSERT OR UPDATE OF status ON job_openings
    FOR EACH ROW EXECUTE FUNCTION jobs_enforce_limit();

-- 6. Recriar política pública de leitura
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

-- 7. Tipos ENUM não são mais utilizados
DROP TYPE IF EXISTS job_status;
DROP TYPE IF EXISTS job_contract_type;
