# 🇧🇷 Patriota Indica - Clube de Negócios & Guia da Livre Iniciativa

Plataforma de indicação local de serviços e produtos por proximidade geográfica e raio de atendimento, com **CADASTRO CURADO, TRIAGEM RIGOROSA E ADESÃO À CARTA DE PRINCÍPIOS E VALORES**.

---

## 🏛️ Visão e Blindagem Jurídica

O **Patriota Indica** opera como uma **Rede de Afinidade e Clube de Negócios Privado**, fundado na **Liberdade de Associação (Art. 5º, XVII da Constituição Federal)** e na **Autonomia Privada e Liberdade Contratual (Art. 421 do Código Civil)**.

- **Carta de Princípios e Valores:** Toda empresa parceira subscreve voluntariamente os 4 pilares:
  1. *Livre Iniciativa & Economia de Mercado*
  2. *Inviolabilidade da Propriedade Privada & Liberdades Individuais*
  3. *Ética Cristã/Ocidental, Família & Retidão Comercial*
  4. *Prosperidade Comunitária & Cooperação Voluntária*
- **Conformidade CDC:** O catálogo e o atendimento ao consumidor final são **universais e irrestritos**, atendendo a qualquer cidadão com excelência, civilidade e sem qualquer discriminação.
- **Conformidade LGPD:** Não armazenamos dados de filiação partidária; apenas a declaração de subscrição e anuência à Carta de Princípios.

---

## 🏗️ Arquitetura do Sistema

```
patriotaindica/
├── backend/                        # API REST assíncrona em FastAPI (Python 3.12)
│   ├── app/
│   │   ├── api/v1/endpoints/       # Busca espacial, empresas, triagem, métricas e auth
│   │   ├── core/                   # Configurações, banco assíncrono e segurança JWT
│   │   ├── models/                 # Modelos SQLAlchemy (PostGIS Geography)
│   │   ├── schemas/                # Schemas Pydantic v2
│   │   └── main.py                 # Ponto de entrada FastAPI com CORS
│   ├── tests/                      # Testes automatizados (pytest)
│   ├── requirements.txt            # Dependências Python
│   ├── Dockerfile
│   └── .env.example
├── frontend/                       # Aplicação Next.js (App Router, SSR/SEO, Tailwind)
│   ├── src/
│   │   ├── app/                    # Rotas: /, /[city]/[category]/[slug], /admin, /painel-empresa, /convite/[token]
│   │   ├── components/             # BusinessProfileView, ManifestoModal
│   │   └── lib/                    # Tipos, mock data e utilitários de distância
│   ├── Dockerfile
│   └── package.json
├── database/                       # Migrations SQL versionadas e Seeds
│   ├── migrations/
│   │   ├── 001_initial_schema.sql         # Tabelas, enums, índices GIST/GIN e triggers
│   │   ├── 002_search_function.sql        # Função PostGIS get_nearby_businesses (KNN <->)
│   │   ├── 003_rls_and_permissions.sql    # Políticas de RLS e reanálise de campos sensíveis
│   │   └── 004_seed_categories.sql        # Taxonomia completa de categorias curadas
│   └── seed/
│       ├── categories.sql                 # Seed de categorias
│       └── sample_businesses_campinas.sql # Dados de teste da cidade piloto (Campinas-SP)
├── docker-compose.yml              # Orquestração PostGIS 16, Redis 7, Backend e Frontend
├── .env.example                    # Modelo unificado de variáveis de ambiente
└── marketplace-local-spec-v2.txt   # Especificação Técnica v2
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
