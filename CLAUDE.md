# CLAUDE.md — Google Ads MCP Server

## Visão Geral do Projeto

Servidor MCP (Model Context Protocol) local para integração com a Google Ads API.
Permite que o Claude acesse e analise dados de campanhas, grupos de anúncios, palavras-chave
e performance diretamente via linguagem natural.

O projeto inclui uma **interface web de setup guiado** (rodando localmente) para que o
usuário configure as credenciais na primeira execução, sem precisar editar arquivos manualmente.

---

## Stack

- **Linguagem:** Python 3.11+
- **MCP SDK:** `mcp` (oficial Anthropic)
- **Google Ads:** `google-ads` (biblioteca oficial Python)
- **Setup UI:** `Flask` + HTML/CSS/JS (interface local de onboarding)
- **Auth:** OAuth2 via Google (credenciais salvas em `.env` local)
- **Config persistence:** arquivo `config.json` local (gitignored)

---

## Estrutura de Diretórios

```
google-ads-mcp/
├── CLAUDE.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── setup_ui/                    # Interface web de configuração inicial
│   ├── app.py                   # Flask server do setup
│   ├── templates/
│   │   ├── index.html           # Passo a passo de configuração
│   │   ├── step_credentials.html
│   │   ├── step_oauth.html
│   │   ├── step_developer_token.html
│   │   ├── step_customer_id.html
│   │   └── success.html
│   └── static/
│       ├── style.css
│       └── script.js
├── server.py                    # Entry point do MCP Server
├── auth/
│   ├── __init__.py
│   ├── oauth.py                 # Fluxo OAuth2 Google
│   └── token_manager.py        # Refresh e persistência de tokens
├── tools/
│   ├── __init__.py
│   ├── campaigns.py             # Tools de campanhas
│   ├── ad_groups.py             # Tools de grupos de anúncios
│   ├── keywords.py              # Tools de palavras-chave
│   ├── performance.py           # Tools de métricas e relatórios
│   ├── search_terms.py          # Tools de termos de busca
│   └── account.py              # Tools de visão geral da conta
├── utils/
│   ├── __init__.py
│   ├── config.py                # Leitura e escrita de config.json
│   ├── gaql.py                  # Helpers para montar queries GAQL
│   └── formatters.py            # Formata respostas para o Claude
└── config.json                  # Gerado pelo setup UI (gitignored)
```

---

## Fases de Implementação

### FASE 1 — Scaffold e README
**Objetivo:** Criar a estrutura base do projeto.

Tarefas:
- [ ] Criar todos os diretórios e arquivos `__init__.py`
- [ ] Gerar `requirements.txt` com todas as dependências
- [ ] Criar `.gitignore` (incluir `config.json`, `.env`, `credentials.json`, `__pycache__`)
- [ ] Criar `.env.example` com todas as variáveis necessárias documentadas
- [ ] Criar `README.md` completo (ver seção README abaixo)
- [ ] Criar `utils/config.py` — funções `load_config()` e `save_config()`

**Dependências do requirements.txt:**
```
mcp>=1.0.0
google-ads>=24.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
flask>=3.0.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
requests>=2.31.0
```

**Validação da fase:** `python -c "import mcp; import flask; import google.ads"` sem erros.

---

### FASE 2 — Interface Web de Setup (Setup UI)
**Objetivo:** Interface local step-by-step para configuração inicial das credenciais.

O setup é um wizard com 4 passos, rodando em `http://localhost:5001`.

**Passos do wizard:**

**Step 1 — Google Cloud Credentials**
- Campo: upload ou paste do conteúdo do `credentials.json`
- Instrução visual com link para o Google Cloud Console
- Validação: verifica se o JSON tem `client_id` e `client_secret`

**Step 2 — Developer Token**
- Campo: input do Developer Token do Google Ads
- Explicação de onde obtê-lo (Google Ads Manager > Ferramentas > API Center)
- Toggle: modo "Test Account" vs "Production"

**Step 3 — OAuth2 Authorization**
- Botão "Autorizar com Google" → abre fluxo OAuth no browser
- Callback em `http://localhost:5001/oauth/callback`
- Salva `refresh_token` no `config.json`
- Mostra checkmark verde após autorização bem-sucedida

**Step 4 — Customer ID**
- Input do Customer ID (formato: `xxx-xxx-xxxx`)
- Se for conta Manager (MCC): campo adicional para `login_customer_id`
- Botão "Testar Conexão" → faz uma query simples e mostra nome da conta

**Success Page:**
- Mostra resumo da configuração
- Exibe o bloco de configuração MCP para colar no `claude_desktop_config.json`
- Botão "Iniciar MCP Server"

**Design da UI:**
- Tema escuro, minimalista, profissional
- Fonte monoespaçada nos campos de token/ID
- Barra de progresso nos passos
- Ícones de status (pendente / ok / erro) por passo
- Cores: fundo `#0f0f0f`, accent `#4285F4` (Google Blue), texto `#e8e8e8`

**Arquivos a criar:**
- `setup_ui/app.py` — Flask app com rotas: `/`, `/step/<n>`, `/oauth/callback`, `/test-connection`, `/save-config`
- Todos os templates HTML
- `setup_ui/static/style.css` e `script.js`

**Validação da fase:** Acessar `http://localhost:5001` e navegar pelos 4 passos sem erro.

---

### FASE 3 — Autenticação Google Ads
**Objetivo:** Módulo de auth robusto usando as credenciais geradas pelo setup.

Tarefas:
- [ ] `auth/oauth.py` — iniciar fluxo OAuth, gerar URL de autorização, trocar code por tokens
- [ ] `auth/token_manager.py` — carregar config.json, fazer refresh automático de token expirado, instanciar `GoogleAdsClient`
- [ ] Função `get_client()` que retorna cliente autenticado pronto para uso

**Lógica de `get_client()`:**
```python
def get_client() -> GoogleAdsClient:
    config = load_config()
    # Monta dict de configuração para o cliente
    # Faz refresh do token se necessário
    # Retorna GoogleAdsClient configurado
```

**Validação da fase:** `python -c "from auth.token_manager import get_client; c = get_client(); print('OK')"`.

---

### FASE 4 — MCP Server + Tools Core
**Objetivo:** Entry point do MCP e as tools principais.

**`server.py`** — Entry point:
```python
from mcp.server.stdio import stdio_server
# Importa todas as tools
# Registra no servidor MCP
# Inicia loop
```

**Tools a implementar (com GAQL correspondente):**

**`tools/account.py`**
- `get_account_summary(customer_id)` → nome, moeda, fuso horário, status
- `list_accessible_customers()` → lista todas as contas acessíveis

**`tools/campaigns.py`**
- `get_campaigns(customer_id, status?)` → id, nome, status, tipo, budget (em reais), data início/fim
- `get_campaign_performance(customer_id, campaign_id, date_range)` → impressões, cliques, CTR, custo, conversões, CPA, ROAS

**`tools/ad_groups.py`**
- `get_ad_groups(customer_id, campaign_id?)` → id, nome, status, CPC máximo
- `get_ad_group_performance(customer_id, ad_group_id, date_range)` → métricas completas

**`tools/keywords.py`**
- `get_keywords(customer_id, ad_group_id?, status?)` → texto, match type, CPC, Quality Score, status
- `get_keyword_performance(customer_id, date_range, campaign_id?)` → métricas por keyword

**`tools/search_terms.py`**
- `get_search_terms(customer_id, date_range, campaign_id?)` → termos reais que ativaram anúncios, impressões, cliques, conversões

**`tools/performance.py`**
- `get_account_performance(customer_id, date_range)` → visão geral com todas as métricas
- `get_performance_by_device(customer_id, date_range)` → breakdown por device
- `get_performance_by_day(customer_id, date_range)` → série temporal diária

**Formato de `date_range`:** string no padrão `"LAST_7_DAYS"`, `"LAST_30_DAYS"`, `"THIS_MONTH"`, `"LAST_MONTH"`, ou `"YYYY-MM-DD,YYYY-MM-DD"`.

**`utils/formatters.py`** — converter micros para reais (÷ 1.000.000), formatar CTR/ROAS como percentual, formatar datas.

**`utils/gaql.py`** — helper `build_date_filter(date_range)` que converte o formato acima em cláusula WHERE do GAQL.

**Validação da fase:** Testar cada tool via `mcp dev server.py` no terminal.

---

### FASE 5 — Tools de Escrita (Write Operations)
**Objetivo:** Tools que modificam dados — implementar com confirmação explícita.

> ⚠️ Toda write operation deve exigir um parâmetro `confirm: bool = False`.
> Se `confirm=False`, retorna um preview da ação sem executar.
> Se `confirm=True`, executa e retorna resultado.

**Tools:**
- `pause_campaign(customer_id, campaign_id, confirm)` → pausa campanha
- `enable_campaign(customer_id, campaign_id, confirm)` → ativa campanha
- `update_campaign_budget(customer_id, campaign_id, new_budget_brl, confirm)` → atualiza budget
- `pause_keyword(customer_id, criterion_id, ad_group_id, confirm)` → pausa keyword
- `add_negative_keyword(customer_id, campaign_id, keyword_text, match_type, confirm)` → adiciona keyword negativa

**Validação da fase:** Testar `pause_campaign` com `confirm=False` e verificar que retorna preview sem modificar nada.

---

### FASE 6 — Polimento e Entrega
**Objetivo:** Projeto pronto para uso real.

Tarefas:
- [ ] Tratar erros da Google Ads API com mensagens legíveis (GoogleAdsException)
- [ ] Logging estruturado em `logs/mcp.log`
- [ ] Script `start.sh` — verifica se config.json existe; se não, abre setup UI; se sim, inicia MCP
- [ ] Script `setup.sh` — instala dependências e abre setup UI pela primeira vez
- [ ] Testar todas as tools em conta real
- [ ] Revisar README com bloco final de configuração do Claude Desktop

**Validação da fase:** Executar `./start.sh` do zero em ambiente limpo e completar setup sem erros.

---

## Regras de Implementação

### Nunca faça
- Nunca hardcode credenciais, tokens ou IDs no código
- Nunca commitar `config.json`, `.env` ou `credentials.json`
- Nunca executar write operations sem o parâmetro `confirm=True`
- Nunca usar `print()` para debug — usar `logging`
- Nunca misturar lógica de autenticação dentro das tools

### Sempre faça
- Sempre ler credenciais via `utils/config.py` → `load_config()`
- Sempre converter valores monetários de micros para BRL nos formatters
- Sempre validar `customer_id` (remover hífens antes de passar à API)
- Sempre incluir `customer_id` como parâmetro explícito em todas as tools
- Sempre retornar dicts estruturados das tools, nunca strings cruas
- Sempre documentar cada tool com docstring descrevendo parâmetros e retorno

### Padrão de retorno das tools
```python
# Sucesso
return {
    "status": "ok",
    "data": [...],
    "meta": {"count": N, "customer_id": "...", "date_range": "..."}
}

# Erro
return {
    "status": "error",
    "error": "Mensagem legível para o Claude",
    "details": str(e)
}
```

---

## Configuração do Claude Desktop (gerada pelo setup)

O setup UI gera automaticamente o bloco abaixo para o usuário colar em
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "python",
      "args": ["/caminho/absoluto/para/google-ads-mcp/server.py"],
      "env": {}
    }
  }
}
```

---

## Variáveis do config.json (gerenciado pelo setup UI)

```json
{
  "client_id": "",
  "client_secret": "",
  "developer_token": "",
  "refresh_token": "",
  "customer_id": "",
  "login_customer_id": "",
  "use_proto_plus": true,
  "test_account": false
}
```

---

## Contexto de Negócio

Este MCP é usado pela agência **Velo** para gerenciar campanhas de Google Ads
de clientes hoteleiros (hotéis, pousadas, resorts) no Brasil.

Isso significa:
- Moeda sempre em BRL
- Métricas relevantes: CPA de reserva, ROAS de campanha, CTR de anúncios de hospedagem
- Customer IDs são de contas cliente dentro de uma MCC (Manager Account)
- O `login_customer_id` é o ID da conta Manager da Velo

---

## Ordem de Execução Recomendada

```
FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6
```

Iniciar sempre pela FASE atual. Não pular fases.
Ao completar uma fase, rodar a validação antes de avançar.
