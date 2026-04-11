"""Entry point do MCP Server para Google Ads."""

import asyncio
import json
import logging
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Diretório raiz do projeto (absoluto, independente do cwd)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE_DIR)

from tools.account import get_account_summary, list_accessible_customers
from tools.campaigns import get_campaigns, get_campaign_performance
from tools.ad_groups import get_ad_groups, get_ad_group_performance
from tools.keywords import get_keywords, get_keyword_performance
from tools.search_terms import get_search_terms
from tools.performance import (
    get_account_performance,
    get_performance_by_device,
    get_performance_by_day,
)
from tools.write_operations import (
    pause_campaign,
    enable_campaign,
    update_campaign_budget,
    pause_keyword,
    add_negative_keyword,
)

# Configura logging para arquivo (path absoluto para funcionar de qualquer cwd)
_LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, "mcp.log")),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# Instancia o servidor MCP
app = Server("google-ads-mcp")

# ─────────────────────────────────────────────
# Definições das Tools (schema para o Claude)
# ─────────────────────────────────────────────

TOOLS = [
    Tool(
        name="get_account_summary",
        description="Retorna resumo da conta Google Ads: nome, moeda, fuso horário e status.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID da conta (ex: 123-456-7890). Opcional se configurado no config.json.",
                }
            },
        },
    ),
    Tool(
        name="list_accessible_customers",
        description="Lista todas as contas Google Ads acessíveis com as credenciais configuradas. Útil para descobrir Customer IDs disponíveis na MCC.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_campaigns",
        description="Lista campanhas da conta com id, nome, status, tipo, budget em BRL e datas de início/fim.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID da conta. Opcional.",
                },
                "status": {
                    "type": "string",
                    "enum": ["ENABLED", "PAUSED", "REMOVED"],
                    "description": "Filtro de status. Se omitido, retorna todas.",
                },
            },
        },
    ),
    Tool(
        name="get_campaign_performance",
        description="Retorna métricas de performance de campanhas: impressões, cliques, CTR, custo em BRL, conversões, CPA e ROAS.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha específica. Se omitido, retorna todas."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
            },
        },
    ),
    Tool(
        name="get_ad_groups",
        description="Lista grupos de anúncios com id, nome, status e CPC máximo em BRL.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha para filtrar. Se omitido, retorna todos."},
            },
        },
    ),
    Tool(
        name="get_ad_group_performance",
        description="Retorna métricas completas de performance por grupo de anúncios.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "ad_group_id": {"type": "string", "description": "ID do ad group específico. Se omitido, retorna todos."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
            },
        },
    ),
    Tool(
        name="get_keywords",
        description="Lista palavras-chave com texto, match type (EXACT/PHRASE/BROAD), CPC máximo em BRL, Quality Score e status.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "ad_group_id": {"type": "string", "description": "ID do ad group para filtrar. Se omitido, retorna todas."},
                "status": {
                    "type": "string",
                    "enum": ["ENABLED", "PAUSED", "REMOVED"],
                    "description": "Filtro de status. Se omitido, retorna todas.",
                },
            },
        },
    ),
    Tool(
        name="get_keyword_performance",
        description="Retorna métricas de performance por palavra-chave: impressões, cliques, CTR, custo em BRL, conversões e CPA.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
                "campaign_id": {"type": "string", "description": "ID da campanha para filtrar. Se omitido, retorna todas."},
            },
        },
    ),
    Tool(
        name="get_search_terms",
        description="Retorna os termos de busca reais que ativaram anúncios. Útil para identificar termos irrelevantes e adicionar como negativos.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
                "campaign_id": {"type": "string", "description": "ID da campanha para filtrar. Se omitido, retorna todos."},
            },
        },
    ),
    Tool(
        name="get_account_performance",
        description="Retorna visão geral consolidada de performance da conta com todas as métricas: impressões, cliques, CTR, custo total em BRL, conversões, CPA e ROAS.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
            },
        },
    ),
    Tool(
        name="get_performance_by_device",
        description="Retorna performance segmentada por dispositivo: mobile, desktop e tablet.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
            },
        },
    ),
    Tool(
        name="get_performance_by_day",
        description="Retorna série temporal diária de performance. Útil para identificar tendências e sazonalidade.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "date_range": {
                    "type": "string",
                    "description": "Intervalo de datas: 'LAST_7_DAYS', 'LAST_30_DAYS', 'THIS_MONTH', 'LAST_MONTH' ou 'YYYY-MM-DD,YYYY-MM-DD'.",
                    "default": "LAST_30_DAYS",
                },
            },
        },
    ),
    # ── Write Operations ──────────────────────────────────────────────────────
    Tool(
        name="pause_campaign",
        description=(
            "⚠️ WRITE OPERATION — Pausa uma campanha ativa. "
            "Com confirm=False (padrão) retorna um preview sem executar. "
            "Use confirm=True para confirmar e executar a ação."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha a ser pausada. Obrigatório."},
                "confirm": {
                    "type": "boolean",
                    "description": "Se false, retorna preview sem executar. Se true, executa a ação.",
                    "default": False,
                },
            },
            "required": ["campaign_id"],
        },
    ),
    Tool(
        name="enable_campaign",
        description=(
            "⚠️ WRITE OPERATION — Ativa (despausa) uma campanha. "
            "Com confirm=False (padrão) retorna um preview sem executar. "
            "Use confirm=True para confirmar e executar a ação."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha a ser ativada. Obrigatório."},
                "confirm": {
                    "type": "boolean",
                    "description": "Se false, retorna preview sem executar. Se true, executa a ação.",
                    "default": False,
                },
            },
            "required": ["campaign_id"],
        },
    ),
    Tool(
        name="update_campaign_budget",
        description=(
            "⚠️ WRITE OPERATION — Atualiza o orçamento diário de uma campanha (em BRL). "
            "Com confirm=False (padrão) retorna um preview sem executar. "
            "Use confirm=True para confirmar e executar a ação."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha. Obrigatório."},
                "new_budget_brl": {
                    "type": "number",
                    "description": "Novo orçamento diário em BRL (ex: 50.00). Obrigatório.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Se false, retorna preview sem executar. Se true, executa a ação.",
                    "default": False,
                },
            },
            "required": ["campaign_id", "new_budget_brl"],
        },
    ),
    Tool(
        name="pause_keyword",
        description=(
            "⚠️ WRITE OPERATION — Pausa uma palavra-chave em um grupo de anúncios. "
            "Com confirm=False (padrão) retorna um preview sem executar. "
            "Use confirm=True para confirmar e executar a ação."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "criterion_id": {"type": "string", "description": "ID do critério (keyword). Obrigatório."},
                "ad_group_id": {"type": "string", "description": "ID do ad group que contém a keyword. Obrigatório."},
                "confirm": {
                    "type": "boolean",
                    "description": "Se false, retorna preview sem executar. Se true, executa a ação.",
                    "default": False,
                },
            },
            "required": ["criterion_id", "ad_group_id"],
        },
    ),
    Tool(
        name="add_negative_keyword",
        description=(
            "⚠️ WRITE OPERATION — Adiciona uma keyword negativa em nível de campanha. "
            "Com confirm=False (padrão) retorna um preview sem executar. "
            "Use confirm=True para confirmar e executar a ação."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID da conta. Opcional."},
                "campaign_id": {"type": "string", "description": "ID da campanha. Obrigatório."},
                "keyword_text": {
                    "type": "string",
                    "description": "Texto da keyword negativa (ex: 'grátis'). Obrigatório.",
                },
                "match_type": {
                    "type": "string",
                    "enum": ["BROAD", "PHRASE", "EXACT"],
                    "description": "Tipo de correspondência. Default: BROAD.",
                    "default": "BROAD",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Se false, retorna preview sem executar. Se true, executa a ação.",
                    "default": False,
                },
            },
            "required": ["campaign_id", "keyword_text"],
        },
    ),
]

# ─────────────────────────────────────────────
# Handlers MCP
# ─────────────────────────────────────────────

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Retorna a lista de tools disponíveis."""
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Despacha a chamada de tool para a função correspondente."""
    logger.info("Tool chamada: %s | args: %s", name, arguments)

    result = await asyncio.get_event_loop().run_in_executor(
        None, _dispatch_tool, name, arguments
    )

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _dispatch_tool(name: str, args: dict) -> dict:
    """Mapeia o nome da tool para a função Python correspondente."""
    dispatch_map = {
        "get_account_summary": lambda: get_account_summary(
            args.get("customer_id")
        ),
        "list_accessible_customers": lambda: list_accessible_customers(),
        "get_campaigns": lambda: get_campaigns(
            args.get("customer_id"),
            args.get("status"),
        ),
        "get_campaign_performance": lambda: get_campaign_performance(
            args.get("customer_id"),
            args.get("campaign_id"),
            args.get("date_range", "LAST_30_DAYS"),
        ),
        "get_ad_groups": lambda: get_ad_groups(
            args.get("customer_id"),
            args.get("campaign_id"),
        ),
        "get_ad_group_performance": lambda: get_ad_group_performance(
            args.get("customer_id"),
            args.get("ad_group_id"),
            args.get("date_range", "LAST_30_DAYS"),
        ),
        "get_keywords": lambda: get_keywords(
            args.get("customer_id"),
            args.get("ad_group_id"),
            args.get("status"),
        ),
        "get_keyword_performance": lambda: get_keyword_performance(
            args.get("customer_id"),
            args.get("date_range", "LAST_30_DAYS"),
            args.get("campaign_id"),
        ),
        "get_search_terms": lambda: get_search_terms(
            args.get("customer_id"),
            args.get("date_range", "LAST_30_DAYS"),
            args.get("campaign_id"),
        ),
        "get_account_performance": lambda: get_account_performance(
            args.get("customer_id"),
            args.get("date_range", "LAST_30_DAYS"),
        ),
        "get_performance_by_device": lambda: get_performance_by_device(
            args.get("customer_id"),
            args.get("date_range", "LAST_30_DAYS"),
        ),
        "get_performance_by_day": lambda: get_performance_by_day(
            args.get("customer_id"),
            args.get("date_range", "LAST_30_DAYS"),
        ),
        # ── Write Operations ──────────────────────────────────────────────
        "pause_campaign": lambda: pause_campaign(
            args.get("customer_id"),
            args.get("campaign_id"),
            args.get("confirm", False),
        ),
        "enable_campaign": lambda: enable_campaign(
            args.get("customer_id"),
            args.get("campaign_id"),
            args.get("confirm", False),
        ),
        "update_campaign_budget": lambda: update_campaign_budget(
            args.get("customer_id"),
            args.get("campaign_id"),
            args.get("new_budget_brl"),
            args.get("confirm", False),
        ),
        "pause_keyword": lambda: pause_keyword(
            args.get("customer_id"),
            args.get("criterion_id"),
            args.get("ad_group_id"),
            args.get("confirm", False),
        ),
        "add_negative_keyword": lambda: add_negative_keyword(
            args.get("customer_id"),
            args.get("campaign_id"),
            args.get("keyword_text"),
            args.get("match_type", "BROAD"),
            args.get("confirm", False),
        ),
    }

    handler = dispatch_map.get(name)
    if handler is None:
        logger.warning("Tool desconhecida: %s", name)
        return {
            "status": "error",
            "error": f"Tool '{name}' não encontrada.",
            "details": f"Tools disponíveis: {list(dispatch_map.keys())}",
        }

    return handler()


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

async def main():
    logger.info("Iniciando Google Ads MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
