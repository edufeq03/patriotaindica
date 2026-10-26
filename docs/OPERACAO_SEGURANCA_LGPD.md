# Patriota Indica - Manual de Operação, Segurança e Conformidade LGPD (M8, M11, M14)

Este documento estabelece as diretrizes de infraestrutura, segurança da informação, rotinas operacionais e conformidade com a Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018) para a plataforma **Patriota Indica**.

---

## 1. Infraestrutura e Blindagem do Servidor (Contabo / VPS / Easypanel)

### 1.1 Firewall do Sistema Operacional (UFW)
Apenas as portas estritamente necessárias devem permanecer expostas à internet:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
# Permitir SSH (recomenda-se alterar a porta padrao 22 para ex: 2222)
sudo ufw allow 2222/tcp comment 'SSH porta segura'
# Permitir trafego HTTP e HTTPS
sudo ufw allow 80/tcp comment 'HTTP Nginx/Traefik'
sudo ufw allow 443/tcp comment 'HTTPS Cloudflare'
sudo ufw enable
```
> **IMPORTANTE**: O PostgreSQL (5432) e o Redis (6379) **NUNCA** devem ter suas portas abertas no firewall do host. Eles devem operar exclusivamente na rede interna do Docker (`internal_net`).

### 1.2 Endurecimento do SSH e Prevenção de Força Bruta
No arquivo `/etc/ssh/sshd_config`:
- `PermitRootLogin no` (bloquear login direto como root)
- `PasswordAuthentication no` (permitir exclusivamente autenticação por chave SSH ed25519)
- `MaxAuthTries 3`
- Instalar e habilitar `fail2ban`:
```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

### 1.3 Atualizações Automáticas de Segurança
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 2. Camada Cloudflare (Borda, WAF e Mitigação DDoS)

1. **DNS Proxied (Nuvem Laranja Ativada):** O IP real do servidor VPS nunca deve ser revelado publicamente. Todos os registros de domínio `patriotaindica.com.br` e `api.patriotaindica.com.br` devem apontar via proxy Cloudflare.
2. **Modo SSL/TLS:** Configurar como **Full (Strict)** na Cloudflare, com certificado Origin Server instalado no servidor.
3. **Firewall WAF Cloudflare:**
   - Habilitar proteção contra bots maliciosos (Bot Fight Mode).
   - Rate limit na borda para rotas de autenticação e pesquisa (`/api/v1/auth/*`, `/api/v1/search/*`).
   - Modo de Emergência ("Under Attack Mode"): Ativar no painel Cloudflare em caso de ataque DDoS coordenado.
4. **Bloqueio de Países Irrelevantes (Geoblocking opcional):** Para o MVP nacional, bloquear ou impor JS Challenge a requisições de origens com alto tráfego de exploração e sem usuários reais (ex: países fora das Américas).

---

## 3. Rotinas de Backup Criptografado e Restauração (M14)

### 3.1 Backup Diário Automatizado
O script `scripts/backup_postgres.sh` realiza o dump do PostgreSQL, aplica compressão gzip, criptografa com AES-256-CBC via OpenSSL e gera hash SHA-256 de integridade.

Agendar no Crontab (`crontab -e`):
```cron
# Backup diario as 03:00 da manha
0 3 * * * BACKUP_ENCRYPTION_KEY="sua-chave-secreta-forte" /home/usuario/patriotaindica/scripts/backup_postgres.sh >> /var/log/patriotaindica_backup.log 2>&1
```

### 3.2 Teste Periódico de Restauração (Mensal)
Conforme boas práticas de compliance, a integridade dos backups deve ser testada mensalmente em ambiente isolado:
```bash
./scripts/restore_postgres.sh /var/backups/patriotaindica/dump_patriotaindica_20261026_030000.sql.gz.enc patriotaindica_restore_test
```

---

## 4. Conformidade LGPD e Tratamento de Dados (M11)

### 4.1 Dados Pessoais Sensíveis (Art. 5º, II da LGPD)
- **Contexto:** A adesão à **Carta de Princípios da Liberdade** por pessoas físicas, autônomos ou Microempreendedores Individuais (MEI) vincula uma identidade pessoal a valores morais, filosóficos e políticos.
- **Base Legal:** Art. 11, inciso I da LGPD (Consentimento específico e destacado).
- **Implementação:**
  1. Checkbox exclusivo e obrigatório no cadastro com texto explícito do Art. 11, I.
  2. Política de Privacidade transparente explicando a finalidade única de integração à rede colaborativa.
  3. Facilidade de revogação de consentimento a qualquer tempo.

### 4.2 Privacidade de MEIs por Padrão (*Privacy by Default*)
- Endereços comerciais de MEIs frequentemente coincidem com a residência familiar.
- O sistema mantém `show_full_address: false` por padrão, exibindo publicamente apenas o Bairro e a Cidade.

### 4.3 Canal do Titular de Dados e Atendimento ao DPO
- **Canal Público:** Página interativa `/privacidade` conectada ao endpoint `POST /api/v1/privacy/request`.
- **E-mail do DPO:** `dpo@patriotaindica.com.br`.
- **Prazo de Atendimento:** Até 15 dias úteis (conforme normativas da ANPD).
- **Tipos de Solicitação Tratadas:**
  - `deletion`: Exclusão definitiva de cadastro e dados pessoais.
  - `revocation`: Revogação da subscrição da Carta de Princípios (com despublicação do perfil).
  - `export`: Exportação completa dos dados pessoais armazenados.
  - `correction`: Retificação cadastral.

---

## 5. Plano de Resposta a Incidentes de Segurança

Em caso de suspeita ou confirmação de incidente envolvendo dados pessoais (ex: invasão, vazamento ou acesso indevido):

1. **Contenção Imediata (Hora 0 a 2):**
   - Isolar o servidor afetado da rede externa ou ativar o "Under Attack Mode" na Cloudflare.
   - Rotacionar imediatamente todas as credenciais de banco, Redis e chaves JWT (`JWT_SECRET_KEY`).
   - Bloquear contas suspeitas na tabela `users`.
2. **Análise Forense e Inventário de Impacto (Hora 2 a 24):**
   - Inspecionar logs do backend e do banco de dados (tabelas `business_review_log`, `audit_logs`).
   - Identificar a natureza dos dados atingidos e o volume de titulares afetados.
3. **Comunicação à ANPD e aos Titulares (Até 3 dias úteis):**
   - Caso o incidente represente risco relevante aos titulares, notificar formalmente a Autoridade Nacional de Proteção de Dados (ANPD) via sistema oficial de peticionamento, detalhando:
     - Natureza dos dados afetados;
     - Medidas de segurança técnicas adotadas antes e após o ocorrido;
     - Riscos aos direitos dos titulares e medidas de mitigação em curso.
