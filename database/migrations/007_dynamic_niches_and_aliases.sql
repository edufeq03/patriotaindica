-- ==============================================================================
-- Migration 007: Dynamic Niches, Aliases and Moderation (Sec. 4)
-- Description:
-- 1. Suporte a nichos de cauda longa propostos por usuários
-- 2. Status 'approved', 'pending', 'rejected' para categorias
-- 3. Tabela category_aliases para sinônimos e mesclagem de nichos pelo Admin
-- ==============================================================================

-- 1. Colunas de moderação de nichos dinâmicos
ALTER TABLE categories ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved';
ALTER TABLE categories ADD COLUMN IF NOT EXISTS proposed_by_business_id UUID REFERENCES businesses(id) ON DELETE SET NULL;

-- 2. Tabela de Aliases (Sinônimos) para Autocomplete e Mesclagem
CREATE TABLE IF NOT EXISTS category_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  alias_name VARCHAR(100) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_category_aliases_name ON category_aliases (alias_name);
CREATE INDEX IF NOT EXISTS idx_categories_status ON categories (status);
