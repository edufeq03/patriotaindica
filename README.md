# 🇧🇷 Patriota Indica - Rede de Negócios Confiáveis & Clube da Livre Iniciativa

Plataforma comunitária de networking e **indicação qualificada de negócios confiáveis**, conectando consumidores e empresas parceiras por proximidade geográfica, com **CADASTRO CURADO, RECOMENDAÇÃO MÚTUA ENTRE PARES E ADESÃO À CARTA DE PRINCÍPIOS E VALORES**.

> 💡 **FILOSOFIA DO PROJETO**: O Patriota Indica **NÃO é um marketplace de leilão de menor preço ou disputa predatória por orçamentos**. Nosso propósito é criar uma **Rede de Negócios Confiáveis**, fortalecendo o empresário e prestador local através de reputação comprovada, indicações entre membros associados e integridade comunitária.

---

## 🏛️ Visão e Blindagem Jurídica

O **Patriota Indica** opera como uma **Rede de Afinidade, Confiança e Clube de Negócios Privado**, fundado na **Liberdade de Associação (Art. 5º, XVII da Constituição Federal)** e na **Autonomia Privada e Liberdade Contratual (Art. 421 do Código Civil)**.

- **Carta de Princípios e Valores:** Toda empresa parceira subscreve voluntariamente os 4 pilares:
  1. *Livre Iniciativa & Economia de Mercado*
  2. *Inviolabilidade da Propriedade Privada & Liberdades Individuais*
  3. *Ética Cristã/Ocidental, Família & Retidão Comercial*
  4. *Prosperidade Comunitária & Cooperação Voluntária*
- **Rede de Indicação e Endosso Mútuo:** Membros da rede recomendam colegas parceiros ("Recomendado por empresas associadas"), criando uma teia de credibilidade orgânica.
- **Conformidade CDC:** O catálogo e o atendimento ao consumidor final são **universais e irrestritos**, atendendo a qualquer cidadão com excelência, civilidade e sem qualquer discriminação.
- **Conformidade LGPD:** Não armazenamos dados de filiação partidária; apenas a declaração de subscrição e anuência à Carta de Princípios, consentimentos auditáveis e canal de opt-out no WhatsApp.

---

## 🚩 Escopo do MVP & Mapa de Módulos (Sprint S3)

O projeto opera sob uma arquitetura enxuta orientada a **Feature Flags** configuráveis em runtime através de variáveis de ambiente:

### 🟢 Módulos do Núcleo Ativo (Core MVP)
1. **Cadastro Unificado e Atômico (`/api/v1/businesses/register`):**
   - Criação simultânea de conta de empresário (`role='owner'`) e negócio (`pending_review`).
   - Suporte a múltiplos negócios vinculados ao mesmo proprietário.
   - Emissão imediata de sessão via cookies `HttpOnly` no BFF do Next.js.
2. **Vitrine Pública Inteligente (`/` e `/search`):**
   - Busca geoespacial com PostGIS, ordenação por raio de proximidade e filtros de nichos.
   - Regra unificada de visibilidade pública (`public_businesses`): exibe apenas negócios aprovados, ativos e sem exclusão lógica.
3. **Módulo de Vagas Locais (`/jobs` e `/painel-empresa`):**
   - Publicação de vagas pelas empresas cadastradas com moderação administrativa e selo "Contratando" nos cards da vitrine.
4. **Triagem Administrativa (`/admin` e `/triage`):**
   - Fila de curadoria com máquina de estados rigorosa, aprovação, rejeição com motivo e notas de auditoria.
5. **Planos & Pagamentos (`FEATURE_PAYMENTS=true`):**
   - Assinaturas e preferências de pagamento via Mercado Pago mantidas ativas para monetização do MVP.
6. **Conformidade LGPD & Integridade:**
   - Exclusão lógica (`deleted_at`), anonimização irreversível de titulares (`/privacy/admin/requests/{id}/anonymize`) e proteção referencial `ON DELETE RESTRICT` para histórico financeiro e fiscal.

### ❄️ Módulos Congelados no MVP (Desativados por Flags)
- `FEATURE_WHATSAPP_BOT=false`: Disparos automáticos e bot de captação de leads.
- `FEATURE_NETWORK=false`: Rede de recomendações e endossos mútuos entre empresas.
- `FEATURE_WAITLIST=false`: Lista de espera por cidades em expansão.
- `FEATURE_ADMIN_TOOLS=false`: Convites VIP e importação em lote CSV legada.

---

## 🏗️ Arquitetura do Sistema

```
patriotaindica/
├── backend/                        # API REST assíncrona em FastAPI (Python 3.12)
│   ├── app/
│   │   ├── api/v1/endpoints/       # Busca PostGIS, empresas, triagem, painel do dono, pagamentos, vagas
│   │   ├── core/                   # Configurações, bootstrap admin, rate limit Redis e JWT
│   │   ├── models/                 # Modelos SQLAlchemy (PostGIS Geography, Jobs, Plans, Users, Business)
│   │   ├── schemas/                # Schemas Pydantic v2 com validação estrita
│   │   └── main.py                 # Ponto de entrada FastAPI com middlewares de segurança OWASP
│   ├── tests/                      # 121+ testes automatizados (pytest + anyio)
│   ├── requirements.txt            # Dependências Python
│   ├── Dockerfile
│   └── .env.example
├── frontend/                       # Aplicação Next.js 16 (Turbopack, SSR/SEO, Tailwind, BFF)
│   ├── src/
│   │   ├── app/                    # Rotas: /, /[city]/[category]/[slug], /admin, /painel-empresa
│   │   ├── components/             # BusinessProfileView, ManifestoModal, BusinessJobsModal
│   │   └── lib/                    # Tipos e utilitários
│   ├── Dockerfile
│   └── package.json
├── database/                       # Migrations SQL versionadas com SHA-256 e controle de drift
│   ├── migrations/                 # 21 migrações SQL (001 a 021_data_integrity.sql)
│   └── scripts/                    # Runner oficial migrate.py
├── scripts/                        # Scripts operacionais: backup AES-256, restore e testes
├── docker-compose.yml              # Orquestração PostGIS 16, Redis 7, Backend e Frontend
└── .env.example                    # Modelo unificado de variáveis de ambiente
```

---

## ⚡ Módulos e Funcionalidades

1. **Vitrine Pública Inteligente (`/`):**
   - Detecção de localização via GPS (`navigator.geolocation`) com fallback para Campinas-SP.
   - Filtros dinâmicos por categoria, raio de atendimento (5, 15, 30, 50 km) e tipo (serviços/produtos).
   - Selos oficiais de *Signatária Patriota Indica* e *Empresa Verificada*.
   - Candidatura espontânea (*Canal C*) com subscrição obrigatória da Carta de Princípios.

2. **Perfis Públicos com SEO Local (`/[city]/[category]/[slug]`):**
   - Metadados dinâmicos e Schema.org `LocalBusiness` estruturado em JSON-LD.
   - Proteção de endereço residencial vs estabelecimento físico comercial.
   - Botão direto para WhatsApp com métrica de contato auditável (`/go/whatsapp/[id]`).
   - Reivindicação de controle (*Canal D*) com simulação de código OTP de 6 dígitos via WhatsApp.
   - Canal de denúncia ética e inconsistência cadastral.

3. **Central do Administrador e Triagem (`/admin`):**
   - Fila de triagem por status (`pending_review`, `needs_info`, `approved`, `rejected`).
   - Dossiê com checklist automático: verificação de duplicidade, CNPJ ativo na BrasilAPI, geocodificação e adesão aos princípios.
   - Cadastro assistido para sementes (*Canal A*).
   - Importação em lote via arquivo CSV.
   - Gerador de convites VIP com token único (*Canal B*).
   - Gerenciamento de categorias em tempo real.

4. **Painel Exclusivo do Lojista (`/painel-empresa`):**
   - Métricas de cliques em WhatsApp, telefone e visualizações do perfil.
   - Botão de pausa/reativação imediata do anúncio na busca pública.
   - Edição de horários, diferenciais e aviso de reanálise para alteração de dados sensíveis.

---

## 🚀 Como Executar Localmente

### Opção 1: Via Docker Compose (Recomendado)
```bash
docker compose up -d
```
- **Frontend:** http://localhost:3000
- **Backend API & Swagger:** http://localhost:8000/docs
- **PostgreSQL PostGIS:** localhost:5432
- **Redis:** localhost:6379

### Opção 2: Execução Direta no Host

#### Backend (Python 3.12):
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Testes do Backend:
```bash
PYTHONPATH=. ./backend/venv/bin/pytest backend/tests
```

#### Frontend (Next.js):
```bash
cd frontend
npm install
npm run dev
```

---

## ☁️ Deploy em VPS com Easypanel

1. Crie um novo projeto no **Easypanel** chamado `patriotaindica`.
2. Adicione um serviço **App** apontando para o seu repositório GitHub:
   - `https://github.com/edufeq03/patriotaindica.git`
3. Configure as variáveis de ambiente baseadas no `.env.example`.
4. O Easypanel detectará o `docker-compose.yml` ou executará os containers do backend e frontend com SSL automático gerenciado pelo Traefik/Caddy nativo do painel.

---

## 📄 Licença
Propriedade privada • Todos os direitos reservados • Patriota Indica © 2026.
