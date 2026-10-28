# Status de Implementação das Sprints - Patriota Indica

> **Data da última atualização**: 28 de Outubro de 2026  
> **Branch**: `main`  
> **Status Remoto**: Atualizado e sincronizado com `origin/main` no GitHub.

---

## 1. Visão Geral do Progresso

| Sprint | Escopo | Status | Testes / Validação |
| :--- | :--- | :---: | :--- |
| **Sprint 0** | Estancar o sangramento (Vulnerabilidades críticas K1, K2, K5, K6, K7, H4, H5, H11) | ✅ Concluída | 53 testes passando (`backend/tests/test_sprint0.py`) |
| **Sprint 1** | Identidade e curadoria à prova de burla (K3, K4, H2, H3, H6, H7, H10, M3) | ✅ Concluída | 66 testes passando (`backend/tests/test_sprint1.py`) |
| **Sprint 2** | Sessão, borda e infraestrutura (H1, H9, M1, M5, M6, M7, M12) | ✅ Concluída | 72 testes passando (`backend/tests/test_sprint2.py`) + `npm run build` OK |
| **Sprint 3** | Busca por proximidade e núcleo do produto (T3.1 a T3.4) | ✅ Concluída | 77 testes passando (`backend/tests/test_sprint3.py`) + PostGIS + Cache Redis |
| **Sprint 4** | Cobrança consistente e valor pago (H8, M8, A2.3) | ⏳ **A INICIAR** | Próxima sprint |
| **Sprint 5** | Bot de orçamento no WhatsApp oficial (Cloud API) | ⏸️ Planejada | Depende da Sprint 4 |
| **Sprint 6** | Redesenho UX e conversão | ⏸️ Planejada | Depende da Sprint 5 |
| **Sprint 7** | Operação, CI/CD, backup e auditoria pré-lançamento | ⏸️ Planejada | (Base de backup & homologação já adiantada) |

---

## 2. Detalhamento do que foi Feito

### Sprint 0 — Estancar o Sangramento (Commit `f2122e1`)
- **T0.1**: Removidos endpoints de risco (`/system/migrate`, `/triage/reset-businesses`, `/triage/test-evolution`, `/search/audit`, `/payments/simulate-activation`) e DDL/UPDATE em runtime no boot.
- **T0.2**: Validação estrita de `JWT_SECRET_KEY` (mínimo 64 caracteres hexadecimais, sem palavras da blocklist), remoção do fallback tolerante no `decode_access_token`.
- **T0.3**: Middleware `X-Request-ID` para rastreamento; sanitização do handler global de exceções (sem vazamento de `str(exc)`); `set_db_app_context` com fail-closed (500).
- **T0.4**: `ALLOWED_HOSTS` sem wildcard `*`; remoção de origens HTTP sem TLS do CORS.
- **T0.5**: Rota pública `/businesses/by-slug/{slug}` restrita estritamente a empresas com status `approved`.
- **T0.6**: Eliminação de backdoor `123456`, código de contingência e dev_code nas respostas HTTP; desacoplamento entre confirmação de OTP e autoaprovação de empresa.
- **T0.7**: Correção dos parâmetros do rate limit no canal do titular LGPD (`/privacy/request`).
- **T0.8**: Organização de especificações na pasta `docs/`.

### Sprint 1 — Identidade e Curadoria à Prova de Burla (Commit `f44c6da`)
- **T1.1 (OTP / Claim)**:
  - Normalização para E.164 (`+55...`) na coluna indexada `whatsapp_e164` (migration 013).
  - OTP seguro no `OTPService`: chave `otp:{sha256(phone)}`, salt criptográfico, 5 tentativas máximas por código com exclusão imediata na 5ª falha.
  - Rate limit de 3 envios/hora por telefone e 10/hora por IP.
  - Resposta genérica anti-enumeração (200 OK idêntico para números existentes ou não).
  - Prevenção de account pre-hijacking (H3): geração de usuário novo e exclusivo por claim com e-mail sintético (`owner-{id}@patriotaindica.internal`).
- **T1.2 (Curadoria & Pausa)**:
  - Adicionada flag `owner_paused: bool` separada de `status`. O proprietário só pode alternar a pausa em anúncios aprovados.
  - Busca pública ([search.py](file:///home/capella/dev/antigravity/patriotaindica/backend/app/api/v1/endpoints/search.py)) e perfil ([businesses.py](file:///home/capella/dev/antigravity/patriotaindica/backend/app/api/v1/endpoints/businesses.py)) filtram estritamente `status == 'approved'` AND `owner_paused.is_(False)`.
  - Selo `is_verified` concedido única e exclusivamente por ação manual do administrador em `/triage/decision`.
- **T1.3 (Edição do Dono)**:
  - `PUT /owner/{id}/profile` aceita exclusivamente dados de baixo risco (`description`, `service_radius_km <= 50`, `logo_url` local em `/static/uploads/...`).
  - Campos de risco (nome, whatsapp, endereço, etc.) passam para `POST /owner/{id}/propose-changes` na tabela `business_pending_changes` com teto de 3 pendências abertas.
- **T1.4 (Documento & Posse)**:
  - Candidatura com documento já existente em outra empresa recebe `document_flag_duplicate = True`.
  - Aprovação na triagem é bloqueada caso o admin não passe `confirm_duplicate_document = True`.
- **T1.5 (Menor Privilégio & DB)**:
  - `docker-compose.yml` sem senhas estáticas de PostgreSQL, usando variáveis de ambiente.
  - Migration 013 com RLS atualizado para `owner_paused = FALSE` e `FORCE ROW LEVEL SECURITY` em `consents`.
- **T1.6 (Consentimentos LGPD)**:
  - Tabela `consents` persistindo aceite auditável da Carta de Princípios, Termos e Privacidade.
  - Três checkboxes obrigatórios no cadastro (`consent_carta_principios`, `consent_termos`, `consent_privacidade`), com erro 422 caso ausentes.
  - Endpoint `POST /privacy/revoke-consent` para revogação, suspendendo e ocultando a empresa da vitrine.
- **T1.7 (Convites Seguros)**:
  - Validade `days_valid` limitada entre 1 e 14 dias.
  - Consumo atômico `UPDATE invitations ... RETURNING` contra race conditions.
  - Vinculação de dono sem conceder selo `is_verified` automático.

### Operação Prévia (Backup e Homologação) (Commit `71fb1e0`)
- [scripts/backup_postgres.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/backup_postgres.sh): backup diário criptografado com AES-256 e hash SHA-256, auto-detecção de container Docker/Easypanel e suporte a Rclone.
- [scripts/restore_postgres.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/restore_postgres.sh): restauração com validação de integridade.
- [.env.staging.example](file:///home/capella/dev/antigravity/patriotaindica/.env.staging.example): template de variáveis para ambiente de homologação isolado.
- [database/scripts/anonymize_for_staging.sql](file:///home/capella/dev/antigravity/patriotaindica/database/scripts/anonymize_for_staging.sql): sanitização de PII para homologação conforme a LGPD.
- [docs/GUIA_BACKUP_E_HOMOLOGACAO.md](file:///home/capella/dev/antigravity/patriotaindica/docs/GUIA_BACKUP_E_HOMOLOGACAO.md): manual operacional.

### Sprint 2 — Sessão, Borda e Infraestrutura (Commit `65102da`)
- **T2.1: Sessão Segura e BFF (Backend-For-Frontend)**:
  - Emissão de par rotativo: Access Token (15 min) + Refresh Token rotativo (7 dias) persistido no Redis com `jti`.
  - Endpoint `POST /api/v1/auth/refresh` (com rotação atômica) e `POST /api/v1/auth/logout`.
  - Rotas BFF no Next.js (`/api/auth/*`) emitindo cookies `HttpOnly; Secure; SameSite=Strict; Path=/`.
  - Remoção de `document.cookie` e isolamento de tokens contra XSS.
- **T2.2: Middleware Next.js & CSP**:
  - Middleware com biblioteca `jose` validando assinaturas JWT para `/admin` e `/painel-empresa`.
  - Injeção transparente do header `Authorization: Bearer <token>` nas requisições do frontend.
  - Cabeçalhos de segurança padrão OWASP e Content Security Policy (CSP).
  - Ocultação dos links públicos para `/admin`.
- **T2.3: Rate Limit Confiável & Infra**:
  - `get_client_ip`: proteção contra IP spoofing (`CF-Connecting-IP` + `TRUSTED_PROXY_HOPS`).
  - Pool persistente de Redis via `lifespan` do FastAPI e script Lua atômico (`INCR` + `EXPIRE`).
  - Fail-closed (HTTP 503) em endpoints críticos caso o Redis falhe em produção.

### Sprint 3 — Busca por Proximidade e Núcleo do Produto
- **T3.1: PostGIS Real e Busca Otimizada**:
  - Eliminação completa de N+1 queries na busca através de `outerjoin` unificado com `categories`.
  - Proximidade real com `ST_DWithin` e cálculo de `distance_km` via `ST_Distance` em coordenadas do usuário.
  - Suporte a cobertura espacial de prestadores com `service_radius_km` e atendimento online.
  - DTO público seguro sem vazamento de colunas de auditoria interna.
- **T3.2: Geocodificação Segura sem Fallback Falso**:
  - Eliminação do ponto padrão hardcoded de Campinas.
  - Endereços não-resolvidos recebem `location_pending = True` para ajuste manual do administrador via triagem.
  - Cache de coordenadas no Redis (`geo:{cep}:{cidade}:{uf}`) com TTL de 30 dias.
  - Suporte para o administrador ajustar coordenadas manuais (`lat`/`lng`) em `/triage/decision`.
- **T3.3: Privacidade e Rastreamento de Contato**:
  - Rotação para entrega segura de contato via `/go/whatsapp/{business_id}` com mitigação anti-bot.
- **T3.4: Cold Start e Expansão por Cidades**:
  - Migration 014 criando tabelas `cities` e `city_waitlist` com RLS e índices GiST.
  - Endpoints `GET /api/v1/cities` e `POST /api/v1/cities/{city_id}/waitlist`.

---

## 3. Próximo Passo: Sprint 4 (Cobrança Consistente e Valor Pago)

Tarefas da Sprint 4:
1. **T4.1: Fonte Única dos Planos**:
   - Modelagem de tabela `plans` e entitlements sem dependência de dicionários estáticos.
2. **T4.2: Entitlements e Benefícios por Assinatura**:
   - Destaque na vitrine, ciclo de vida da assinatura (`active`, `grace_period`, `expired`).
3. **T4.3: Endurecimento do Webhook do Mercado Pago**:
   - Validação de `x-signature` (HMAC-SHA256) contra replay attacks.
   - Idempotência transacional estrita em `payments` evitando creditações duplicadas.
