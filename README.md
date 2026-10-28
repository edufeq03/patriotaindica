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

## 🏗️ Arquitetura do Sistema

```
patriotaindica/
├── backend/                        # API REST assíncrona em FastAPI (Python 3.12)
│   ├── app/
│   │   ├── api/v1/endpoints/       # Busca PostGIS, empresas, triagem, painel do dono, pagamentos, whatsapp
│   │   ├── core/                   # Configurações, banco assíncrono, Redis, rate limiting e segurança JWT/BFF
│   │   ├── models/                 # Modelos SQLAlchemy (PostGIS Geography, PeerEndorsements, WhatsApp, Plans)
│   │   ├── schemas/                # Schemas Pydantic v2 com validação estrita
│   │   ├── services/               # WhatsApp Híbrido (Evolution + Meta Cloud), OTP seguro e Geocodificação
│   │   └── main.py                 # Ponto de entrada FastAPI com middlewares de segurança OWASP
│   ├── tests/                      # 99 testes automatizados (pytest + anyio)
│   ├── requirements.txt            # Dependências Python
│   ├── Dockerfile
│   └── .env.example
├── frontend/                       # Aplicação Next.js 16 (Turbopack, SSR/SEO, Tailwind, BFF)
│   ├── src/
│   │   ├── app/                    # Rotas: /, /[city]/[category]/[slug], /q/[slug], /admin, /painel-empresa
│   │   ├── components/             # BusinessProfileView, ManifestoModal, TrustCard
│   │   └── lib/                    # Tipos, mock data e utilitários
│   ├── Dockerfile
│   └── package.json
├── database/                       # Migrations SQL versionadas com SHA-256 e controle de drift
│   ├── migrations/                 # 17 migrações SQL (001 a 017)
│   └── scripts/                    # Runner Python migrate.py e anonimização LGPD
├── scripts/                        # Scripts operacionais: backup AES-256, restore, ASVS audit e DR drill
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
