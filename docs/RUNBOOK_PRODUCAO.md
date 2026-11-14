# 📖 Runbook de Produção • Patriota Indica

Guia operacional oficial para deploy, configuração de segurança, backup, restauração e rotação de credenciais no ambiente de produção (Easypanel / Docker Swarm / VPS).

---

## 1. Topologia de Serviços no Easypanel

O ambiente de produção é estruturado em 4 containers isolados na mesma rede Docker (`easypanel-network`):

| Serviço | Imagem / Build | Porta Interna | Volumes Persistentes | Healthcheck |
| :--- | :--- | :--- | :--- | :--- |
| **`db`** | `postgis/postgis:16-3.4` | `5432` | `postgres_data:/var/lib/postgresql/data` | `pg_isready -U postgres` |
| **`redis`** | `redis:7-alpine` | `6379` | `redis_data:/data` | `redis-cli ping` |
| **`backend`** | Dockerfile (`backend/Dockerfile`) | `8000` | `uploads_data:/app/static/uploads` | `GET /health` |
| **`frontend`** | Dockerfile (`frontend/Dockerfile`) | `3000` | N/A | `GET /api/health` |

---

## 2. Dicionário de Variáveis de Ambiente Obrigatórias

Nenhum segredo padrão é aceito. Cada variável deve ser provisionada via interface de ambiente do Easypanel ou `.env`.

### 🗄️ Banco de Dados e Cache
```env
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=gere_uma_senha_forte_aqui
POSTGRES_DB=patriotaindica

REDIS_URL=redis://:senha_do_redis@redis:6379/0
REDIS_PASSWORD=senha_do_redis
```

### 🔐 Segurança e Autenticação
```env
# Gere com: openssl rand -hex 64 (Mínimo de 64 caracteres hexadecimais)
JWT_SECRET_KEY=e83a45c7b912f4e6d302a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
TRUSTED_PROXY_HOPS=1

# Conta do Administrador Principal (Sincronizado automaticamente no startup)
ADMIN_EMAIL=admin@patriotaindica.com.br
ADMIN_PASSWORD=SenhaAdminForteEMulticaracteres2026!
```

### 🚩 Feature Flags do MVP (Sprint S3)
```env
FEATURE_PAYMENTS=true
FEATURE_WHATSAPP_BOT=false
FEATURE_NETWORK=false
FEATURE_WAITLIST=false
FEATURE_ADMIN_TOOLS=false
```

### 🌐 Frontend (Next.js BFF)
```env
# URL interna acessível apenas entre containers Docker
INTERNAL_API_URL=http://backend:8000/api/v1
NEXT_PUBLIC_APP_URL=https://patriotaindica.com.br
JWT_SECRET_KEY=mesma_chave_gerada_acima_com_64_chars
```

---

## 3. Inicialização e Migrações do Banco

1. **Criação do Banco de Dados no PostgreSQL**:
   Na primeira inicialização do serviço `db`, se o banco não for criado automaticamente pelo `POSTGRES_DB`, execute via console do container:
   ```bash
   psql -U postgres -c "CREATE DATABASE patriotaindica;"
   psql -U postgres -d patriotaindica -c "CREATE EXTENSION IF NOT EXISTS postgis;"
   psql -U postgres -d patriotaindica -c "CREATE EXTENSION IF NOT EXISTS unaccent;"
   ```

2. **Aplicação das Migrations (001 a 021)**:
   O script oficial `database/scripts/migrate.py` executa de forma transacional idempotente, calculando o hash SHA-256 de cada arquivo e registrando em `schema_migrations`:
   ```bash
   # Dentro do container do backend:
   python3 database/scripts/migrate.py
   ```
   *(Ou executado automaticamente no startup do container backend).*

---

## 4. Rotina de Backup e Recuperação de Desastres (DR)

### 📦 Procedimento de Backup (Diário - Cron)

Execute o script de backup automatizado ou rode manualmente:
```bash
#!/bin/bash
BACKUP_DIR="/backups/patriotaindica/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 1. Dump binário comprimido do PostgreSQL
docker exec -t $(docker ps -qf "name=db") pg_dump -U postgres -d patriotaindica -Fc -Z 9 > "$BACKUP_DIR/db_patriotaindica.dump"

# 2. Cópia das fotos e imagens enviadas pelos lojistas
docker cp $(docker ps -qf "name=backend"):/app/static/uploads "$BACKUP_DIR/uploads"
tar -czvf "$BACKUP_DIR/uploads.tar.gz" -C "$BACKUP_DIR" uploads
rm -rf "$BACKUP_DIR/uploads"

echo "Backup concluído com sucesso em $BACKUP_DIR"
```

### 🔄 Procedimento de Restauração a Frio (Disaster Recovery)

Para restaurar o banco de dados a partir de um arquivo `.dump`:
```bash
# 1. Interrompa o backend para cessar escrita
# 2. Restaure o banco de dados
pg_restore -U postgres -d patriotaindica --clean --if-exists "$BACKUP_DIR/db_patriotaindica.dump"

# 3. Restaure o volume de uploads
docker cp "$BACKUP_DIR/uploads.tar.gz" $(docker ps -qf "name=backend"):/app/static/
# Descompacte dentro do container em /app/static/uploads
```

---

## 5. Rotação de Segredos e Contingência

### Rotação do `JWT_SECRET_KEY`
1. Gere um novo segredo forte:
   ```bash
   openssl rand -hex 64
   ```
2. Atualize a variável `JWT_SECRET_KEY` simultaneamente nas configurações do **backend** e do **frontend** no Easypanel.
3. Clique em **Implantar** em ambos os serviços.
4. *(Efeito esperado)*: Todos os usuários e administradores ativos terão suas sessões encerradas por segurança e precisarão realizar login novamente com e-mail e senha.

### Redefinição de Senha do Administrador
Para trocar a senha do administrador:
1. Altere o valor de `ADMIN_PASSWORD` nas variáveis de ambiente do backend no Easypanel.
2. Reinicie o serviço `backend`. O método `ensure_admin()` na inicialização atualizará o hash `password_hash` no PostgreSQL com bcrypt de forma atômica.

---

## 6. Monitoramento de Saúde (Healthchecks)

- **Backend**:
  `GET http://backend:8000/health`
  - Resposta esperada: `HTTP 200 OK`
  - Payload: `{"status":"online","service":"Patriota Indica","environment":"production","version":"2.0.0"}`

- **Frontend**:
  `GET http://frontend:3000/api/health`
  - Resposta esperada: `HTTP 200 OK`
  - Payload: `{"status":"ok","time":"..."}`

- **Portas e Roteamento no Easypanel**:
  - `backend`: Porta **8000**, domínio de API (ex: `api.patriotaindica.com.br`).
  - `frontend`: Porta **3000**, domínio principal (ex: `patriotaindica.com.br`).

