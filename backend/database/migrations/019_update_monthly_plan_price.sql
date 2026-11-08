-- ==============================================================================
-- Migration 019: Update Monthly Plan Price
-- Description: Ajusta o valor do plano mensal de R$ 15,00 para R$ 14,90 (1490 centavos).
-- ==============================================================================

UPDATE plans
SET 
  price_cents = 1490,
  monthly_equivalent_cents = 1490,
  updated_at = NOW()
WHERE id = 'mensal';
