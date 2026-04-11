"""Tools de campanhas Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import (
    format_status,
    format_campaign_type,
    micros_to_brl,
    build_metrics_summary,
)
from utils.gaql import build_date_filter

logger = logging.getLogger(__name__)


def get_campaigns(customer_id: str | None = None, status: str | None = None) -> dict:
    """Lista campanhas da conta com id, nome, status, tipo, budget e datas.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        status: Filtro de status: "ENABLED", "PAUSED", "REMOVED". Se omitido, retorna todas.

    Returns:
        Dict com status, data (lista de campanhas) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.amount_micros,
                campaign_budget.delivery_method
            FROM campaign
            ORDER BY campaign.name
        """

        if status:
            query += f" WHERE campaign.status = '{status.upper()}'"

        response = ga_service.search(customer_id=cid, query=query)
        campaigns = []

        for row in response:
            c = row.campaign
            b = row.campaign_budget
            campaigns.append({
                "id": str(c.id),
                "name": c.name,
                "status": format_status(c.status),
                "type": format_campaign_type(c.advertising_channel_type),
                "budget_brl": micros_to_brl(b.amount_micros),
                "start_date": c.start_date or None,
                "end_date": c.end_date or None,
            })

        return {
            "status": "ok",
            "data": campaigns,
            "meta": {
                "count": len(campaigns),
                "customer_id": cid,
                "status_filter": status or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar campanhas: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível listar as campanhas.",
            "details": format_api_error(e),
        }


def get_campaign_performance(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Retorna métricas de performance de uma ou todas as campanhas.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha específica. Se omitido, retorna todas.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").

    Returns:
        Dict com status, data (lista de performance por campanha) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE {date_filter}
        """

        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"

        query += " ORDER BY metrics.cost_micros DESC"

        response = ga_service.search(customer_id=cid, query=query)
        results = []

        for row in response:
            c = row.campaign
            m = row.metrics
            metrics = build_metrics_summary(
                impressions=m.impressions,
                clicks=m.clicks,
                cost_micros=m.cost_micros,
                conversions=m.conversions,
                conversion_value_micros=int(m.conversions_value * 1_000_000),
            )
            metrics["average_cpc_brl"] = micros_to_brl(m.average_cpc)
            results.append({
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "status": format_status(c.status),
                **metrics,
            })

        return {
            "status": "ok",
            "data": results,
            "meta": {
                "count": len(results),
                "customer_id": cid,
                "date_range": date_range,
                "campaign_id": campaign_id or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance de campanhas: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a performance das campanhas.",
            "details": format_api_error(e),
        }
