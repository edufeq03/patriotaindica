-- ==============================================================================
-- Migração 017: Sprint 7 - Rede de Negócios Confiáveis e Endosso Entre Pares
-- Objetivo: Fortalecer a comunidade com indicações mútuas, disponibilidade imediata
--           e reputação coletiva, sem leilão de menor preço.
-- ==============================================================================

-- 1. Campos de Disponibilidade Imediata e Rede em 'businesses'
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS availability_until TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS network_badge VARCHAR(50) NOT NULL DEFAULT 'membro_verificado',
ADD COLUMN IF NOT EXISTS endorsements_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_businesses_availability ON businesses(availability_until) 
WHERE availability_until IS NOT NULL;

-- 2. Tabela de Endossos e Recomendações Mútuas entre Empresas Parceiras
CREATE TABLE IF NOT EXISTS peer_endorsements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endorsing_business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    endorsed_business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    relationship_type VARCHAR(30) NOT NULL DEFAULT 'peer' 
        CHECK (relationship_type IN ('client', 'partner', 'peer', 'supplier')),
    testimonial VARCHAR(500) NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_no_self_endorsement CHECK (endorsing_business_id != endorsed_business_id),
    CONSTRAINT uq_peer_endorsement UNIQUE (endorsing_business_id, endorsed_business_id)
);

CREATE INDEX IF NOT EXISTS idx_peer_endorsements_endorsed ON peer_endorsements(endorsed_business_id);
CREATE INDEX IF NOT EXISTS idx_peer_endorsements_endorsing ON peer_endorsements(endorsing_business_id);

-- 3. Habilitar RLS
ALTER TABLE peer_endorsements ENABLE ROW LEVEL SECURITY;

-- Política de Leitura Pública: apenas endossos públicos onde ambas as empresas estão aprovadas
DROP POLICY IF EXISTS peer_endorsements_public_read ON peer_endorsements;
CREATE POLICY peer_endorsements_public_read ON peer_endorsements
    FOR SELECT
    USING (
        is_public = TRUE
        AND EXISTS (
            SELECT 1 FROM businesses b1 
            WHERE b1.id = peer_endorsements.endorsed_business_id 
              AND b1.status = 'approved' 
              AND b1.owner_paused = FALSE
        )
        AND EXISTS (
            SELECT 1 FROM businesses b2 
            WHERE b2.id = peer_endorsements.endorsing_business_id 
              AND b2.status = 'approved'
        )
    );

-- Política de Modificação: apenas a aplicação / dono autenticado
DROP POLICY IF EXISTS peer_endorsements_app_write ON peer_endorsements;
CREATE POLICY peer_endorsements_app_write ON peer_endorsements
    FOR ALL
    USING (current_user = 'app_user' OR current_user = 'postgres');

-- 4. Função e Trigger para atualizar contador 'endorsements_count' automaticamente
CREATE OR REPLACE FUNCTION update_endorsements_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = NEW.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = NEW.endorsed_business_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = OLD.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = OLD.endorsed_business_id;
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        UPDATE businesses 
        SET endorsements_count = (
            SELECT COUNT(*) FROM peer_endorsements 
            WHERE endorsed_business_id = NEW.endorsed_business_id AND is_public = TRUE
        )
        WHERE id = NEW.endorsed_business_id;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_endorsements_count ON peer_endorsements;
CREATE TRIGGER trg_update_endorsements_count
AFTER INSERT OR UPDATE OR DELETE ON peer_endorsements
FOR EACH ROW EXECUTE FUNCTION update_endorsements_count();
