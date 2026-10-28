# Guia Prático de Backup e Ambiente de Homologação (Staging)

Este guia foi elaborado para viabilizar a entrada em operação segura e imediata da plataforma **Patriota Indica**, detalhando a governança de backups e a infraestrutura de homologação.

---

## 1. Ambiente de Homologação (Staging)

O ambiente de homologação permite validar novas features, testar cadastros, fluxo de pagamento do Mercado Pago (em Sandbox) e atualizações de código antes de publicar para os usuários reais em produção.

### 1.1 Topologia Recomendada no Easypanel / VPS

No Easypanel, a melhor prática é criar **dois projetos distintos**:

1. **`patriotaindica` (Produção)**
   - Domínios: `patriotaindica.com.br` e `api.patriotaindica.com.br`
   - Serviços: `db` (Postgres 16 + PostGIS), `redis`, `backend`, `frontend`
   - Branch Git: `main`

2. **`patriotaindica-staging` (Homologação)**
   - Domínios: `staging.patriotaindica.com.br` (ou subdomínio `.easypanel.host`)
   - Serviços isolados: `db-staging`, `redis-staging`, `backend-staging`, `frontend-staging`
   - Branch Git: `develop` ou `staging`
   - Variáveis: baseadas no arquivo [.env.staging.example](file:///home/capella/dev/antigravity/patriotaindica/.env.staging.example)

> [!IMPORTANT]
> **Nunca compartilhe o Banco de Dados ou o Redis entre Homologação e Produção.**
> Manter instâncias separadas evita vazamento de dados, colisão de sessões JWT e envios acidentais de notificações reais durante testes.

### 1.2 Variáveis e Modo Sandbox em Homologação
- **Mercado Pago**: utilize chaves de teste (`TEST-...`) do portal de desenvolvedores do Mercado Pago.
- **JWT_SECRET_KEY**: gere uma chave exclusiva para staging (`openssl rand -hex 64`).
- **ENVIRONMENT**: defina como `staging`.

### 1.3 Carga de Dados no Ambiente de Homologação

Há duas maneiras de inicializar o banco de homologação:

* **Opção 1 (Banco Limpo com Categorias)**:
  Basta subir o container com as migrações automáticas da pasta `database/migrations/`. As categorias oficiais já serão povoadas via migration `004_seed_categories.sql`.
  
* **Opção 2 (Clone Sanitizado de Produção)**:
  Para testar cenários reais sem violar a LGPD:
  1. Gere um dump de produção com `scripts/backup_postgres.sh`.
  2. Restaure no banco de staging com `scripts/restore_postgres.sh`.
  3. Execute o script de anonimização:
     ```bash
     psql -U postgres -d patriotaindica_staging -f database/scripts/anonymize_for_staging.sql
     ```
     *(Este script mascara CPFs, telefones e e-mails de clientes reais e reseta senhas de teste).*

---

## 2. Estratégia de Backup para Entrada em Operação

Para iniciar a operação com resiliência total contra perda de dados ou desastres:

### 2.1 Scripts Prontos no Repositório

* [scripts/backup_postgres.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/backup_postgres.sh):
  - Gera dump comprimido (`.sql.gz`).
  - Criptografa o arquivo com **AES-256-CBC (PBKDF2)** via OpenSSL caso a variável `BACKUP_ENCRYPTION_KEY` esteja definida.
  - Gera hash SHA-256 para verificação de integridade (`.sha256`).
  - Remove automaticamente backups locais com mais de 30 dias (rotatividade).
  - Suporta envio remoto para S3 / Wasabi / B2 via `rclone`.

* [scripts/restore_postgres.sh](file:///home/capella/dev/antigravity/patriotaindica/scripts/restore_postgres.sh):
  - Descriptografa com a senha informada, confere o hash SHA-256 e restaura os dados validando a contagem de tabelas.

### 2.2 Agendamento no Servidor (Cron)

No servidor VPS (ou via agendador de tarefas do Easypanel):

```bash
# Editar o crontab do host
crontab -e

# Adicionar linha para execução diária às 03:00 da madrugada:
0 3 * * * BACKUP_ENCRYPTION_KEY="sua_chave_secreta_de_backup" /home/usuario/patriotaindica/scripts/backup_postgres.sh >> /var/log/patriotaindica_backup.log 2>&1
```

### 2.3 Cópia Externa (Offsite Disaster Recovery)

Para proteger os dados mesmo em caso de falha do datacenter da VPS:
1. Instale o `rclone` no servidor (`curl https://rclone.org/install.sh | sudo bash`).
2. Configure um bucket remoto no Wasabi, Backblaze B2, AWS S3 ou Google Drive (`rclone config`).
3. Adicione `RCLONE_REMOTE_DEST="meubucket:patriotaindica-backups/"` na execução do script. O script enviará os dumps criptografados automaticamente após cada geração.

---

## 3. Próximo Passo na Implementação

Com a infraestrutura de backup e staging documentada e automatizada, estamos prontos para prosseguir na esteira de código com a **Sprint 2 (Sessão Segura, BFF no Next.js e Rate Limit)**.
