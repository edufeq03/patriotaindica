# Status de Implementação das Sprints - Patriota Indica

> **Data da última atualização**: 28 de Outubro de 2026  
> **Branch**: `main`  
> **Último Commit**: `f44c6da` (feat(security): implementa Sprint 1 - identidade e curadoria à prova de burla (T1.1 a T1.7))  
> **Status Remoto**: Atualizado e sincronizado com `origin/main` no GitHub.

---

## 1. Visão Geral do Progresso

| Sprint | Escopo | Status | Testes / Validação |
| :--- | :--- | :---: | :--- |
| **Sprint 0** | Estancar o sangramento (Vulnerabilidades críticas K1, K2, K5, K6, K7, H4, H5, H11) | ✅ Concluída | 53 testes passando (`backend/tests/test_sprint0.py`) |
| **Sprint 1** | Identidade e curadoria à prova de burla (K3, K4, H2, H3, H6, H7, H10, M3) | ✅ Concluída | 66 testes passando (`backend/tests/test_sprint1.py`) |
| **Sprint 2** | Sessão, borda e infraestrutura (H1, H9, M1, M5, M6, M7, M12) | ⏳ **A INICIAR** | Próximo passo após religar |
| **Sprint 3** | Busca por proximidade e núcleo do produto | ⏸️ Planejada | Depende da Sprint 2 |
| **Sprint 4** | Cobrança consistente e valor pago | ⏸️ Planejada | Depende da Sprint 3 |
| **Sprint 5** | Bot de orçamento no WhatsApp oficial (Cloud API) | ⏸️ Planejada | Depende da Sprint 4 |
| **Sprint 6** | Redesenho UX e conversão | ⏸️ Planejada | Depende da Sprint 5 |
| **Sprint 7** | Operação, CI/CD, backup e auditoria pré-lançamento | ⏸️ Planejada | Encerramento |

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

---

## 3. Onde Continuar Depois (Sprint 2 - Imediata)

Ao religar o computador, você pode dizer simplesmente:
> *"Pode continuar com a Sprint 2."*

### Tarefas da Sprint 2 — Sessão, Borda e Infraestrutura:
1. **T2.1: Sessão Segura (BFF no Next.js)**:
   - Eliminar `sessionStorage` e `document.cookie` inseguros com tokens JWT no JavaScript do frontend.
   - Criar rotas BFF no Next.js (`/api/auth/*`) emitindo cookies `HttpOnly`, `Secure` e `SameSite=Strict`.
   - Access token curto (15 min) + refresh token rotativo no Redis com lista de revogação (`jti`).
2. **T2.2: Middleware e CSP de Verdade**:
   - Atualizar `middleware.ts` para validar JWT e role via biblioteca `jose`, protegendo rotas `/admin` e `/painel-empresa`.
   - Implementar cabeçalho Content Security Policy (CSP) com nonce dinâmico por requisição (sem `unsafe-inline`), bloqueando `object-src 'none'`, `base-uri 'self'`.
   - Ocultar links públicos para `/admin`.
3. **T2.3: Rate Limit Confiável e Infra**:
   - `get_client_ip`: não confiar cegamente no primeiro item de `X-Forwarded-For`. Implementar `TRUSTED_PROXY_HOPS` e validação de peers de proxy.
   - Redis com cliente persistente único via lifespan FastAPI (sem abrir e fechar conexões a cada requisição).
   - Operações `INCR` + `EXPIRE` em pipeline atômico.
   - Fail-closed (HTTP 503) em endpoints críticos (login, OTP, cadastro) caso o Redis fique inoperante.

---

## 4. Comandos Úteis de Verificação ao Ligar

Para conferir o estado do projeto no terminal:

```bash
# 1. Verificar histórico do Git
git status
git log -n 2

# 2. Executar suíte de testes (66 testes verdes)
PYTHONPATH=. backend/venv/bin/pytest backend/tests

# 3. Testar build do frontend
cd frontend && npm run build
```
