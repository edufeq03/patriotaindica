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
| **Sprint 4** | Cobrança consistente e valor pago (H8, M8, A2.3) | ✅ Concluída | 84 testes passando (`backend/tests/test_sprint4.py`) + Webhook Mercado Pago HMAC |
| **Sprint 5** | WhatsApp híbrido e Concierge da Rede de Confiança | ✅ Concluída | 91 testes passando (`backend/tests/test_sprint5.py`) + Provedor Híbrido |
| **Sprint 6** | Qualidade de código, DevEx e governança (T6.1 a T6.3) | ✅ Concluída | 95 testes passando (`backend/tests/test_sprint6.py`) + Runner de Migração & Drift Check |
| **Sprint 7** | Rede de Negócios, Recomendações Mútuas e Go-Live | ✅ Concluída | 99 testes passando (`backend/tests/test_sprint7.py`) + ASVS L1 + DR Drill + `/q/[slug]` |

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

## 3. Sprint 4: Cobrança Consistente e Valor Pago (Concluída)

- **T4.1: Fonte Única dos Planos (`plans`)**:
  - [database/migrations/015_sprint4_plans_and_payments.sql](file:///home/capella/dev/antigravity/patriotaindica/database/migrations/015_sprint4_plans_and_payments.sql): ampliou a tabela `plans` com colunas de entitlements (`description`, `badge`, `is_featured`, `search_priority`, `max_categories`, `max_photos`, `has_leads_access`, `has_metrics_access`, `has_banner_access`).
  - Preços consolidados em centavos (`price_cents`: 1500, 7794, 11988). Dicionário hardcoded estático substituído pela consulta direta à tabela `plans` no endpoint `GET /api/v1/payments/plans`.
- **T4.2: Entitlements e Ciclo de Vida da Assinatura**:
  - Modelagem de ciclo de vida com 4 estados em `Subscription`:
    - `active`: vigência em dia.
    - `grace_period`: 3 dias de tolerância com benefícios mantidos para evitar churn imediato.
    - `expired`: após o período de carência.
    - `canceled`: cancelado manualmente ou por reembolso/estorno.
  - Vitrine de busca (`/api/v1/search`): empresas pertencentes a donos com planos pagos ganham selo "Destaque" (`is_featured: True`), badge correspondente e prioridade na ordenação (`search_priority: 30, 20, 10`). Empresas sem plano continuam listadas para preservar a densidade (`is_featured: False`, `search_priority: 1`).
- **T4.3: Endurecimento do Webhook Mercado Pago**:
  - Validação rigorosa do cabeçalho `x-signature` com algoritmo HMAC-SHA256 e segredo `MERCADO_PAGO_WEBHOOK_SECRET` sobre o manifest `id:{data_id};request-id:{x_request_id};ts:{ts};`.
  - Validação estrita de moeda (`currency_id == "BRL"`) e conferência de valor pago em centavos contra o preço do plano, rejeitando tentativas de adulteração de preço (`price_tampered`).
  - Tabela `payments(mp_payment_id UNIQUE, ...)` garantindo idempotência transacional (`INSERT ... ON CONFLICT (mp_payment_id) DO NOTHING`). Webhooks duplicados são reconhecidos com `already_processed` sem duplicar prorrogações.
  - Tratamento de estorno/reembolso (`refunded`, `charged_back`, `cancelled`) revogando imediatamente o período e marcando assinatura como `canceled`.
- **T4.4: URLs de Retorno Confiáveis**:
  - `back_urls` e `notification_url` originam-se estritamente de `settings.PUBLIC_APP_URL`, blindando o sistema contra injeção de `Origin` forjado.
- **T4.5: Indicação Anti-Fraude (Member-Get-Member)**:
  - Vinculação de `referred_user_id` em indicações pendentes durante a reivindicação de empresa (`verify-otp`).
  - Bloqueio de auto-indicação (`referrer == referred`, ou colisão de CPF/CNPJ ou telefone) marcando como `fraud_blocked`.
  - Concessão de +30 dias ao indicador SOMENTE quando a empresa indicada for aprovada e efetuar pagamento de plano, com teto de 12 meses acumulados.

---

## 4. Sprint 5: WhatsApp Híbrido, Bot de Orçamento e Leads (Concluída)

- **T5.1 & T5.2: Arquitetura de Provedor Híbrido Desacoplado**:
  - Implementado o pacote [backend/app/services/whatsapp/](file:///home/capella/dev/antigravity/patriotaindica/backend/app/services/whatsapp) com padrão Strategy/Driver:
    - `EvolutionWhatsAppProvider`: para operação piloto/imediata com custo zero da Meta via QR Code.
    - `MetaCloudWhatsAppProvider`: para operação oficial via Graph API v19+ com verificação Meta Business.
    - `ConsoleWhatsAppProvider`: fallback offline para desenvolvimento e testes.
    - `get_whatsapp_service()`: factory que seleciona o driver por `WHATSAPP_PROVIDER`.
  - Webhook oficial unificado em [whatsapp.py](file:///home/capella/dev/antigravity/patriotaindica/backend/app/api/v1/endpoints/whatsapp.py):
    - `GET /api/v1/webhooks/whatsapp`: responde ao desafio `hub.challenge` com validação de `hub.verify_token`.
    - `POST /api/v1/webhooks/whatsapp`: valida assinatura criptográfica `X-Hub-Signature-256` (HMAC-SHA256) contra forjamento e deduplica eventos na tabela `wa_events`.
- **T5.3: Bot Conversacional de Orçamentos e Matching de Leads**:
  - Máquina de estados conversacional ([bot.py](file:///home/capella/dev/antigravity/patriotaindica/backend/app/services/whatsapp/bot.py)) com persistência de contexto em Redis (e fallback em memória):
    - Captação de necessidade e localização (suporta pin de coordenadas nativo do WhatsApp ou texto).
    - Despacho de pedido de orçamento para até 3 empresas aprovadas na categoria e região, priorizando assinantes com planos ativos.
    - Concorrência justa: o primeiro lojista a responder `ACEITAR <CODIGO>` fecha o pedido com exclusividade (`status = "matched"`), liberando contatos de ambos os lados no WhatsApp e notificando os demais concorrentes de que o pedido foi encerrado.
- **T5.4 & T5.7: Métricas de SLA, Resumo de Pedidos e Selo "Responde Rápido"**:
  - Tabela `lead_offers` com registro de `sent_at`, `responded_at` e cálculo de `response_seconds`.
  - Endpoint `GET /api/v1/webhooks/whatsapp/owner/leads-summary` calculando taxa de aceite, média de resposta e ativando o selo "Responde Rápido" para lojistas ágeis (mínimo 3 ofertas, taxa >= 60% e resposta <= 300s).
- **T5.1 & LGPD: Gestão de Opt-in / Opt-out**:
  - Tabela `wa_optins`: envio de palavras-chave como `PARAR`, `SAIR` ou `CANCELAR` revoga o opt-in imediatamente e silencia o bot; `VOLTAR` reativa o canal.

---

## 5. Sprint 6: Qualidade de Código, DevEx e Governança (Concluída)

- **T6.1: Runner de Migrações Idempotente e Detecção de Drift**:
  - Criado [database/scripts/migrate.py](file:///home/capella/dev/antigravity/patriotaindica/database/scripts/migrate.py) com controle de versão na tabela `schema_migrations`.
  - Armazena checksum SHA-256 de cada migração executada.
  - Modo `--check-drift` para verificação em pipelines de CI/CD: acusa erro se alguma migração já aplicada foi alterada no código-fonte.
  - Script [scripts/run_migrations.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/run_migrations.sh) integrado, capaz de rodar via ambiente virtual Python ou container Docker psql.
- **T6.2: DTOs Blindados e Proibição de Vazamento ORM**:
  - Modelos ORM não são expostos diretamente em endpoints públicos.
  - DTOs específicos filtram colunas de auditoria interna e dados sensíveis (`status`, notas administrativas, histórico de triagem).
- **T6.3: Auditoria Final de Rotas de Risco**:
  - Validação de que endpoints de risco legados (`/system/migrate`, `/triage/reset-businesses`, etc.) respondem estritamente com HTTP 404 Not Found.

---

## 6. Sprint 7: Rede de Negócios, Recomendações Mútuas e Go-Live (Concluída)

- **T7.1: Selo "Disponível Agora" / Plantão Imediato (`availability_until`)**:
  - Implementado no backend (`POST /api/v1/owner/{business_id}/availability`): ativação flexível por 1 a 24 horas para prestadores de atendimento emergencial (chaveiros, guinchos, mecânica rápida, plantão).
  - Vitrine e perfil exibem o selo verde ativo de atendimento de imediato.
- **T7.2: Endossos e Recomendações Mútuas Entre Pares (`peer_endorsements`)**:
  - Migração `017_sprint7_business_network_and_endorsements.sql` criando tabela `peer_endorsements` com RLS, validação anti-autoindicação e trigger automático de contagem.
  - Endpoints no painel (`POST /api/v1/owner/{business_id}/endorsements`, `DELETE`) permitindo que empresas e profissionais da rede recomendem colegas parceiros da comunidade.
  - Endpoint público `GET /api/v1/businesses/by-slug/{slug}/endorsements`: exibe a lista de recomendações comprovadas de outros empresários da rede ("Recomendado por X empresas parceiras"), gerando uma teia de reputação e confiança inatacável.
- **T7.3: Cartão Digital de Confiança e Link de Bio (`/q/{slug}`)**:
  - Rota `GET /api/v1/businesses/by-slug/{slug}/trust-card` fornecendo os dados consolidados de reputação.
  - Página Next.js 16 (`frontend/src/app/q/[slug]/page.tsx`) ultra-rápida, com visual refinado, selo de verificação da rede, contagem de indicações entre pares, link direto de WhatsApp com texto pré-definido de confiança e compatibilidade com QR Codes para balcões e frotas.
- **T7.4: Auditoria Automatizada OWASP ASVS Nível 1**:
  - Script executável [scripts/audit_security_asvs.py](file:///home/capella/dev/antigravity/patriotaindica/scripts/audit_security_asvs.py) validando cabeçalhos de segurança, mitigação de enumeração, rate limiting, anti-tampering em webhooks e ausência de vazamento de erros. 100% aprovado.
- **T7.5: Ensaio de Simulação de Disaster Recovery (DR Drill)**:
  - Script executável [scripts/test_disaster_recovery.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/test_disaster_recovery.sh) executando teste ponta a ponta: dump representativo -> criptografia AES-256-CBC PBKDF2 -> checksum SHA-256 -> detecção e bloqueio de adulteração -> descriptografia e restauração atômica. 100% aprovado.

---

## 7. Status do Roadmap de Engenharia

Todas as 8 sprints planejadas (Sprint 0 à Sprint 7) foram concluídas com sucesso. O sistema possui 99 testes automatizados verdes, compilação de frontend 100% limpa no Next.js 16 e arquitetura pronta para ativação imediata em produção.


