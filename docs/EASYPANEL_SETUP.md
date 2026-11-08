# Guia de Deploy e Manutenção no Easypanel (Serviços Independentes)

Este guia documenta como provisionar, conectar e manter os serviços do **Patriota Indica** de forma desacoplada no **Easypanel**.

---

## 🏗️ 1. Arquitetura de Serviços no Easypanel

Em vez de um monólito via Compose, o projeto é estruturado em **4 serviços independentes** dentro do mesmo **Project** no Easypanel:

1. **`db`** (PostgreSQL 16 com extensão PostGIS)
2. **`redis`** (Redis 7 com senha)
3. **`backend`** (FastAPI / Python 3.12)
4. **`frontend`** (Next.js 15 / Node.js 22)

> **Regra do Easypanel:** Todos os serviços criados dentro de um mesmo Projeto compartilham automaticamente uma rede Docker interna. Eles se comunicam diretamente pelos seus nomes de serviço (`db`, `redis`, `backend`, `frontend`).

---

## 🚀 2. Passo a Passo de Criação no Easypanel

Crie um novo **Project** no Easypanel com o nome **`patriotaindica`** e adicione os 4 serviços:

### Serviço 1: PostgreSQL (`db`)
1. No painel, clique em **+ Service** -> Selecione **PostgreSQL** (ou crie como **App** com imagem personalizada).
2. **Nome do Serviço:** `db`
3. **Imagem Docker:** `postgis/postgis:16-3.4` *(Obrigatório ter PostGIS para buscas geoespaciais)*.
4. **Environment Variables:**
   ```env
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=defina_uma_senha_forte_aqui
   POSTGRES_DB=patriotaindica
   ```
5. **Volume:** O Easypanel criará automaticamente um volume montado em `/var/lib/postgresql/data`.

---

### Serviço 2: Redis (`redis`)
1. Clique em **+ Service** -> Selecione **Redis** (ou **App** com imagem `redis:7-alpine`).
2. **Nome do Serviço:** `redis`
3. **Imagem Docker:** `redis:7-alpine`
4. **Command / Argumentos:**
   ```bash
   redis-server --appendonly yes --requirepass defina_uma_senha_forte_redis
   ```
5. **Environment Variables:**
   ```env
   REDIS_PASSWORD=defina_uma_senha_forte_redis
   ```
6. **Volume:** Montado em `/data`.

---

### Serviço 3: Backend (`backend`)
1. Clique em **+ Service** -> Selecione **App** (Source: **GitHub**).
2. Conecte ao seu repositório: `seu-usuario/patriotaindica` (branch: `main`).
3. **Build:**
   - **Build Method:** Dockerfile
   - **Context Directory:** `/` (raiz do repositório)
   - **Dockerfile Path:** `backend/Dockerfile`
4. **Porta Interna:** `8000`
5. **Environment Variables:**
   ```env
   PROJECT_NAME=Patriota Indica
   ENVIRONMENT=production
   DEBUG=false

   # Banco de Dados (Substitua pela senha definida no serviço db)
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=defina_uma_senha_forte_aqui
   POSTGRES_DB=patriotaindica
   DATABASE_URL=postgresql+asyncpg://postgres:defina_uma_senha_forte_aqui@db:5432/patriotaindica
   DATABASE_SYNC_URL=postgresql://postgres:defina_uma_senha_forte_aqui@db:5432/patriotaindica

   # Redis (Substitua pela senha definida no serviço redis)
   REDIS_PASSWORD=defina_uma_senha_forte_redis
   REDIS_URL=redis://:defina_uma_senha_forte_redis@redis:6379/0

   # JWT Security (Gere uma chave com pelo menos 64 caracteres)
   JWT_SECRET_KEY=f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782

   # Administrador Padrão
   ADMIN_EMAIL=admin@patriotaindica.com.br
   ADMIN_PASSWORD=defina_sua_senha_admin
   ```
6. *Nota:* O container do backend executa automaticamente as migrações SQL pendentes na inicialização via `database/scripts/migrate.py`.

---

### Serviço 4: Frontend (`frontend`)
1. Clique em **+ Service** -> Selecione **App** (Source: **GitHub**).
2. Conecte ao repositório: `seu-usuario/patriotaindica` (branch: `main`).
3. **Build:**
   - **Build Method:** Dockerfile
   - **Context Directory:** `frontend`
   - **Dockerfile Path:** `frontend/Dockerfile`
4. **Porta Interna:** `3000`
5. **Domínios (Domains):**
   - Adicione seu domínio de produção (ex: `patriotaindica.com.br` e `www.patriotaindica.com.br`).
   - Habilite **HTTPS / Let's Encrypt**.
6. **Environment Variables:**
   ```env
   # Comunicação interna via rede do Easypanel
   INTERNAL_API_URL=http://backend:8000/api/v1
   NEXT_PUBLIC_API_URL=/api/v1

   # JWT e Admin (Devem ser idênticos aos do Backend)
   JWT_SECRET_KEY=f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782
   ADMIN_EMAIL=admin@patriotaindica.com.br
   ADMIN_PASSWORD=defina_sua_senha_admin
   ```

---

## 🛠️ 3. Procedimentos de Manutenção e Solução de Problemas

### A. Resetar / Recriar o Banco de Dados do Zero
Se precisar limpar o banco e recriar com migrações limpas:
1. Vá no serviço **`db`** -> Aba **Volumes**.
2. Clique no volume `/var/lib/postgresql/data` e clique em **Delete**.
3. Clique em **Deploy** no serviço `db`.
4. Em seguida, clique em **Restart** no serviço `backend` (ele reaplicará todas as 20 migrações automaticamente).

### B. Como Rodar Migrações Manualmente (se necessário)
Caso adicione uma nova migration em `database/migrations`:
1. Dê **Deploy** no serviço `backend` (o script `entrypoint.sh` executa `migrate.py` ao subir).
2. Ou entre no terminal do serviço `backend` no Easypanel (Aba **Console**) e execute:
   ```bash
   python database/scripts/migrate.py
   ```

### C. Troca de Senhas
- Se alterar a senha do Postgres no serviço **`db`**, altere simultaneamente no `DATABASE_URL` do **`backend`**.
- Se alterar a senha do Redis no serviço **`redis`**, altere simultaneamente no `REDIS_PASSWORD` e `REDIS_URL` do **`backend`**.
- Se alterar a chave `JWT_SECRET_KEY`, altere tanto no **`backend`** quanto no **`frontend`**.

### D. Visualização de Logs
- **Logs do Frontend:** Exibe requisições SSR, páginas acessadas e eventuais proxies do Next.js.
- **Logs do Backend:** Exibe rotas FastAPI acessadas, erros HTTP e conexões com o Postgres/Redis.
