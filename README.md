# Google Ads MCP Server

Servidor MCP (Model Context Protocol) local que conecta o **Claude** diretamente à **Google Ads API**.

Gerencie e analise campanhas, grupos de anúncios, palavras-chave e performance de contas de clientes via linguagem natural — sem abrir nenhum painel.

---

## O que é isso?

Este projeto implementa um servidor MCP local em Python que expõe tools do Google Ads para o Claude Desktop. Uma vez configurado, você pode conversar com o Claude como se estivesse falando com um analista de mídia paga, pedindo dados, relatórios e até executando ações (com confirmação explícita).

**Tools disponíveis:**
- Visão geral da conta (moeda, fuso, status)
- Listar e filtrar campanhas
- Performance de campanhas, ad groups e keywords
- Termos de busca reais que ativaram anúncios
- Breakdown por device e série temporal diária
- Ações de escrita: pausar campanhas, atualizar budgets, adicionar keywords negativas (sempre com confirmação)

---

## Pré-requisitos

- **Python 3.11+**
- **Conta Google Ads** com acesso à API habilitado
- **Developer Token** do Google Ads ([como obter →](https://developers.google.com/google-ads/api/docs/get-started/dev-token))
- **Projeto no Google Cloud** com OAuth2 Desktop App configurado ([como criar →](https://developers.google.com/google-ads/api/docs/oauth/cloud-project))
- **Claude Desktop** instalado

---

## Instalação e Primeira Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/LuanVelo/mcp-mkt-gads.git
cd mcp-mkt-gads
```

### 2. Execute o setup guiado

```bash
./setup.sh
```

O script vai:
- Criar e ativar um virtualenv (`.venv/`)
- Instalar todas as dependências do `requirements.txt`
- Abrir automaticamente a interface de configuração em `http://localhost:5001`

### 3. Configure via wizard (4 passos)

Acesse `http://localhost:5001` no browser e siga o wizard:

| Passo | O que fazer |
|-------|-------------|
| 1 — Google Cloud Credentials | Cole o conteúdo do seu `credentials.json` (OAuth2 Desktop App) |
| 2 — Developer Token | Insira o Developer Token da API do Google Ads |
| 3 — Autorização OAuth | Clique em "Autorizar com Google" e aprove o acesso |
| 4 — Customer ID | Informe o ID da conta cliente (e o ID da Manager/MCC se aplicável) |

Ao finalizar o passo 4, o wizard exibe o bloco de configuração pronto para colar no Claude Desktop.

### 4. Configure o Claude Desktop

Cole o bloco gerado pelo setup em:

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Formato do bloco (o setup preenche os caminhos automaticamente):

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "/caminho/para/mcp-mkt-gads/.venv/bin/python",
      "args": ["/caminho/para/mcp-mkt-gads/server.py"],
      "env": {}
    }
  }
}
```

> **Dica:** rode `pwd` dentro da pasta do projeto para obter o caminho absoluto correto.

### 5. Reinicie o Claude Desktop

O servidor Google Ads MCP estará disponível na próxima sessão.

---

## Como usar no Terminal

Após a primeira configuração, você pode iniciar e testar o servidor direto pelo terminal.

**Iniciar o servidor:**
```bash
./start.sh
```

O script detecta automaticamente se o `config.json` já existe:
- **Existe** → inicia o MCP Server direto
- **Não existe** → abre o setup UI novamente

**Testar o servidor em modo dev (com inspetor interativo):**
```bash
source .venv/bin/activate
mcp dev server.py
```

Isso abre o MCP Inspector no browser, onde você pode chamar cada tool manualmente, ver os parâmetros aceitos e inspecionar as respostas — útil para depurar antes de conectar ao Claude.

**Verificar se as dependências estão instaladas:**
```bash
source .venv/bin/activate
python -c "import mcp; import flask; import google.ads; print('OK')"
```

---

## Como usar com Claude

Com o MCP configurado no Claude Desktop, basta conversar normalmente. O Claude vai chamar as tools automaticamente conforme necessário.

**Relatórios e análises:**
```
Liste todas as campanhas ativas da conta 123-456-7890
Qual foi o ROAS das campanhas do último mês?
Compare a performance por device nos últimos 30 dias
Mostre a série diária de cliques e custo desta semana
Qual foi o CPA médio de reserva no mês passado?
```

**Palavras-chave e termos de busca:**
```
Quais keywords têm Quality Score abaixo de 5?
Mostre os termos de busca que geraram mais conversões essa semana
Quais termos de busca tiveram cliques mas zero conversão no último mês?
```

**Ações de escrita (sempre com confirmação):**
```
Pause a campanha 'Hotel - Branded'
Atualize o budget da campanha 'Search - Genérico' para R$ 150/dia
Adicione 'grátis' como keyword negativa na campanha 'Hotel - Branded'
```

Para ações de escrita, o Claude sempre mostra um **preview da ação antes de executar** e pede confirmação explícita. Nada é modificado sem sua aprovação.

---

## Operações de Escrita (Write Operations)

Toda ação que modifica dados exige confirmação explícita:

```
# Preview (não executa nada)
pause_campaign(customer_id="...", campaign_id="...", confirm=False)

# Executa de verdade
pause_campaign(customer_id="...", campaign_id="...", confirm=True)
```

O Claude sempre vai mostrar um preview da ação e pedir confirmação antes de executar qualquer modificação.

---

## Estrutura do Projeto

```
mcp-mkt-gads/
├── server.py                    # Entry point do MCP Server
├── setup.sh                     # Instalação inicial + abertura do setup UI
├── start.sh                     # Inicia o servidor (abre setup se necessário)
├── requirements.txt
├── .env.example                 # Variáveis de ambiente documentadas
├── auth/
│   ├── oauth.py                 # Fluxo OAuth2 Google
│   └── token_manager.py        # Refresh automático de tokens
├── tools/
│   ├── account.py               # Visão geral da conta
│   ├── campaigns.py             # Campanhas
│   ├── ad_groups.py             # Grupos de anúncios
│   ├── keywords.py              # Palavras-chave
│   ├── search_terms.py          # Termos de busca
│   ├── performance.py           # Métricas e relatórios
│   └── write_operations.py      # Ações de escrita com confirmação
├── utils/
│   ├── config.py                # Leitura/escrita de config.json
│   ├── gaql.py                  # Helpers para queries GAQL
│   ├── formatters.py            # Formatação de respostas (micros → BRL, etc.)
│   └── errors.py                # Tratamento de erros da API
├── setup_ui/                    # Interface web de configuração
│   ├── app.py                   # Flask server do wizard
│   ├── templates/               # HTML dos 4 passos + success page
│   └── static/                  # CSS e JS da interface
└── config.json                  # Gerado pelo setup (gitignored)
```

---

## Configuração Manual (alternativa ao wizard)

Se preferir configurar sem o wizard, crie um `config.json` na raiz do projeto:

```json
{
  "client_id": "seu_client_id.apps.googleusercontent.com",
  "client_secret": "seu_client_secret",
  "developer_token": "seu_developer_token",
  "refresh_token": "seu_refresh_token",
  "customer_id": "1234567890",
  "login_customer_id": "9876543210",
  "use_proto_plus": true,
  "test_account": false
}
```

> **Importante:** o `customer_id` deve ser informado **sem hífens** (ex: `1234567890`, não `123-456-7890`).

---

## Variáveis de Configuração

| Campo | Descrição |
|-------|-----------|
| `client_id` | OAuth2 Client ID do Google Cloud |
| `client_secret` | OAuth2 Client Secret do Google Cloud |
| `developer_token` | Developer Token da API do Google Ads |
| `refresh_token` | Token de refresh OAuth2 (gerado pelo setup) |
| `customer_id` | ID da conta Google Ads do cliente (sem hífens) |
| `login_customer_id` | ID da conta Manager/MCC (se aplicável) |
| `use_proto_plus` | Usar proto-plus (recomendado: `true`) |
| `test_account` | Modo conta de teste (`false` para produção) |

---

## Segurança

- `config.json` e `credentials.json` são **gitignored** por padrão — nunca são versionados
- Tokens são armazenados apenas localmente na sua máquina
- Write operations sempre exigem `confirm=True` explícito — nunca executam silenciosamente
- Nenhum dado trafega para servidores externos além da própria Google Ads API

---

## Troubleshooting

**`config.json` não encontrado ao iniciar:**
Execute `./setup.sh` novamente para refazer a configuração.

**Erro de autenticação OAuth (`invalid_grant`):**
O refresh token pode ter expirado. Execute `./setup.sh` e repita o passo 3 (OAuth).

**`GoogleAdsException: Request made by customer without account access`:**
Verifique se o `login_customer_id` está correto e se a conta Manager tem acesso à conta cliente.

**Porta 5001 já em uso ao abrir o setup:**
```bash
lsof -ti:5001 | xargs kill -9
./setup.sh
```

---

## Contexto

Desenvolvido para uso interno da agência **[Velo](https://velodigital.com.br)** para gerenciar campanhas de Google Ads de clientes hoteleiros (hotéis, pousadas, resorts) no Brasil.

- Moeda sempre em BRL
- Métricas-foco: CPA de reserva, ROAS de campanha, CTR de anúncios de hospedagem
- Acesso via Manager Account (MCC) da Velo
