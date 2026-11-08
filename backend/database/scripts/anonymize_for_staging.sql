-- ==============================================================================
-- Patriota Indica - Sanitização de Dados para Homologação (LGPD Compliance)
-- Executar este script APENAS no banco de Homologação/Staging após restaurar dump de produção.
-- ==============================================================================

BEGIN;

-- 1. Anonimizar Usuários
UPDATE users
SET 
    email = 'user_' || id || '@homolog.local',
    full_name = 'Usuário Teste ' || id,
    phone = '+551199999' || lpad((id % 10000)::text, 4, '0')
WHERE email NOT LIKE '%@patriotaindica.com%' AND role != 'admin';

-- 2. Anonimizar Empresas (contatos reais e documentos)
UPDATE businesses
SET 
    whatsapp = '1199999' || lpad((id % 10000)::text, 4, '0'),
    whatsapp_e164 = '+551199999' || lpad((id % 10000)::text, 4, '0'),
    document = lpad((id % 100000000000)::text, 14, '0')
WHERE status != 'rejected';

-- 3. Limpar logs de auditoria e requisições LGPD com dados reais
TRUNCATE TABLE lgpd_requests;

-- 4. Definir senha padrão segura de teste para contas não-admin ('Teste123!@#')
-- Hash bcrypt de teste para agilizar validações no ambiente de testes
UPDATE users
SET hashed_password = '$2b$12$K89eMvXF8xWf3o9pL2.MxeC6fF1KxVd.m7M2fJp7yR4xH5s6T0hKe'
WHERE role != 'admin';

COMMIT;
