-- 021_data_integrity.sql
-- Sprint S2: Integridade de Dados, Exclusão Lógica, FKs RESTRICT, Índices e Visão Canônica

CREATE EXTENSION IF NOT EXISTS unaccent;

-- 1) Índice idempotente de job_reports (T0.1 / D1)
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_report_daily
  ON job_reports (job_id, ip_hash, ((created_at AT TIME ZONE 'UTC')::date));

-- 2) Limpeza preventiva de órfãos e aplicação de NOT NULL
DELETE FROM business_review_log WHERE business_id IS NULL;
DELETE FROM contact_events      WHERE business_id IS NULL;
DELETE FROM invitations         WHERE business_id IS NULL;
DELETE FROM lead_offers         WHERE lead_id IS NULL OR business_id IS NULL;
DELETE FROM lead_reviews        WHERE lead_id IS NULL OR business_id IS NULL;
DELETE FROM referrals           WHERE referred_business_id IS NULL;
DELETE FROM reports             WHERE business_id IS NULL;
DELETE FROM subscriptions       WHERE owner_user_id IS NULL OR plan_id IS NULL;

ALTER TABLE business_review_log ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE contact_events      ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE invitations         ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE lead_offers         ALTER COLUMN lead_id SET NOT NULL, ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE lead_reviews        ALTER COLUMN lead_id SET NOT NULL, ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE referrals           ALTER COLUMN referred_business_id SET NOT NULL;
ALTER TABLE reports             ALTER COLUMN business_id SET NOT NULL;
ALTER TABLE subscriptions       ALTER COLUMN owner_user_id SET NOT NULL, ALTER COLUMN plan_id SET NOT NULL;

-- 3) Exclusão lógica (deleted_at)
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE users      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_businesses_deleted_at ON businesses (deleted_at);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users (deleted_at);

-- 4) FKs de auditoria e financeiro como RESTRICT (não apaga auditoria/financeiro em cascata)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'business_review_log_business_id_fkey') THEN
        ALTER TABLE business_review_log DROP CONSTRAINT business_review_log_business_id_fkey;
    END IF;
    ALTER TABLE business_review_log ADD CONSTRAINT business_review_log_business_id_fkey
        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE RESTRICT;

    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'job_review_log_job_id_fkey') THEN
        ALTER TABLE job_review_log DROP CONSTRAINT job_review_log_job_id_fkey;
    END IF;
    ALTER TABLE job_review_log ADD CONSTRAINT job_review_log_job_id_fkey
        FOREIGN KEY (job_id) REFERENCES job_openings(id) ON DELETE RESTRICT;

    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'payments_user_id_fkey') THEN
        ALTER TABLE payments DROP CONSTRAINT payments_user_id_fkey;
    END IF;
    ALTER TABLE payments ADD CONSTRAINT payments_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'subscriptions_owner_user_id_fkey') THEN
        ALTER TABLE subscriptions DROP CONSTRAINT subscriptions_owner_user_id_fkey;
    END IF;
    ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_owner_user_id_fkey
        FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT;
END $$;

-- 5) Cidade por FK
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS city_id UUID REFERENCES cities(id) ON DELETE SET NULL;
UPDATE businesses b SET city_id = c.id FROM cities c
 WHERE b.city_id IS NULL AND b.state = c.state
   AND lower(unaccent(b.city)) = lower(unaccent(c.name));
CREATE INDEX IF NOT EXISTS idx_businesses_city_id ON businesses (city_id);

-- 6) Constraints CHECK de Status e Papéis
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role') THEN
        ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('admin','owner','user'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_subscriptions_status') THEN
        ALTER TABLE subscriptions ADD CONSTRAINT ck_subscriptions_status CHECK (status IN ('active', 'past_due', 'canceled', 'trialing'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_payments_status') THEN
        ALTER TABLE payments ADD CONSTRAINT ck_payments_status CHECK (status IN ('pending', 'approved', 'authorized', 'in_process', 'in_mediation', 'rejected', 'cancelled', 'refunded', 'charged_back'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_leads_status') THEN
        ALTER TABLE leads ADD CONSTRAINT ck_leads_status CHECK (status IN ('new', 'matched', 'closed', 'expired'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_reports_status') THEN
        ALTER TABLE reports ADD CONSTRAINT ck_reports_status CHECK (status IN ('pending', 'investigating', 'resolved', 'dismissed'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_categories_status') THEN
        ALTER TABLE categories ADD CONSTRAINT ck_categories_status CHECK (status IN ('approved', 'pending_curation', 'rejected'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cities_status') THEN
        ALTER TABLE cities ADD CONSTRAINT ck_cities_status CHECK (status IN ('active', 'soon', 'inactive'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_data_subject_requests_status') THEN
        ALTER TABLE data_subject_requests ADD CONSTRAINT ck_data_subject_requests_status CHECK (status IN ('pending', 'in_progress', 'completed', 'rejected'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_business_pending_changes_status') THEN
        ALTER TABLE business_pending_changes ADD CONSTRAINT ck_business_pending_changes_status CHECK (status IN ('pending', 'pending_review', 'approved', 'rejected'));
    END IF;
END $$;

-- 7) Unicidade
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_subscription_one_active
  ON subscriptions (owner_user_id) WHERE status = 'active';
CREATE UNIQUE INDEX IF NOT EXISTS uq_business_whatsapp_name
  ON businesses (whatsapp_e164, lower(name)) WHERE deleted_at IS NULL;

-- 8) Índices de Foreign Keys (Performance e Locks)
CREATE INDEX IF NOT EXISTS idx_bpc_proposed_by ON business_pending_changes (proposed_by_user_id);
CREATE INDEX IF NOT EXISTS idx_bpc_reviewed_by ON business_pending_changes (reviewed_by);
CREATE INDEX IF NOT EXISTS idx_brl_admin ON business_review_log (admin_id);
CREATE INDEX IF NOT EXISTS idx_biz_reviewed_by ON businesses (reviewed_by);
CREATE INDEX IF NOT EXISTS idx_cat_proposed_by_biz ON categories (proposed_by_business_id);
CREATE INDEX IF NOT EXISTS idx_alias_category ON category_aliases (category_id);
CREATE INDEX IF NOT EXISTS idx_ce_job ON contact_events (job_id);
CREATE INDEX IF NOT EXISTS idx_inv_created_by ON invitations (created_by);
CREATE INDEX IF NOT EXISTS idx_inv_used_by ON invitations (used_by_user_id);
CREATE INDEX IF NOT EXISTS idx_job_created_by ON job_openings (created_by);
CREATE INDEX IF NOT EXISTS idx_lr_lead ON lead_reviews (lead_id);
CREATE INDEX IF NOT EXISTS idx_leads_matched_biz ON leads (matched_business_id);
CREATE INDEX IF NOT EXISTS idx_pay_business ON payments (business_id);
CREATE INDEX IF NOT EXISTS idx_pay_plan ON payments (plan_id);
CREATE INDEX IF NOT EXISTS idx_ref_referred_biz ON referrals (referred_business_id);
CREATE INDEX IF NOT EXISTS idx_ref_referred_user ON referrals (referred_user_id);
CREATE INDEX IF NOT EXISTS idx_ref_referrer_biz ON referrals (referrer_business_id);
CREATE INDEX IF NOT EXISTS idx_reports_resolved_by ON reports (resolved_by);
CREATE INDEX IF NOT EXISTS idx_sub_business ON subscriptions (business_id);
CREATE INDEX IF NOT EXISTS idx_sub_plan ON subscriptions (plan_id);

-- 9) Regra Única de Visibilidade Pública (T2.5)
CREATE OR REPLACE VIEW public_businesses AS
SELECT b.*
  FROM businesses b
 WHERE b.status = 'approved'
   AND b.deleted_at IS NULL
   AND (b.owner_paused IS FALSE OR b.owner_paused IS NULL);

