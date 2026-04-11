"""Tools de grupos de anúncios Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import format_status, micros_to_brl, build_metrics_summary
from utils.gaql import build_date_filter

logger = logging.getLogger(__name__)


def get_ad_groups(
    customer_id: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    """Lista grupos de anúncios com id, nome, status e CPC máximo.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha para filtrar. Se omitido, retorna todos os grupos.

    Returns:
        Dict com status, data (lista de ad groups) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.cpc_bid_micros,
                campaign.id,
                campaign.name
            FROM ad_group
        """

        if campaign_id:
            query += f" WHERE campaign.id = {campaign_id}"

        query += " ORDER BY ad_group.name"

        response = ga_service.search(customer_id=cid, query=query)
        ad_groups = []

        for row in response:
            ag = row.ad_group
            c = row.campaign
            ad_groups.append({
                "id": str(ag.id),
                "name": ag.name,
                "status": format_status(ag.status),
                "max_cpc_brl": micros_to_brl(ag.cpc_bid_micros),
                "campaign_id": str(c.id),
                "campaign_name": c.name,
            })

        return {
            "status": "ok",
            "data": ad_groups,
            "meta": {
                "count": len(ad_groups),
                "customer_id": cid,
                "campaign_id": campaign_id or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar ad groups: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível listar os grupos de anúncios.",
            "details": format_api_error(e),
        }


def get_ad_group_performance(
    customer_id: str | None = None,
    ad_group_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Retorna métricas completas de performance por grupo de anúncios.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        ad_group_id: ID do ad group específico. Se omitido, retorna todos.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").

    Returns:
        Dict com status, data (lista de performance por ad group) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.average_cpc
            FROM ad_group
            WHERE {date_filter}
        """

        if ad_group_id:
            query += f" AND ad_group.id = {ad_group_id}"

        query += " ORDER BY metrics.cost_micros DESC"

        response = ga_service.search(customer_id=cid, query=query)
        results = []

        for row in response:
            ag = row.ad_group
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
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "status": format_status(ag.status),
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                **metrics,
            })

        return {
            "status": "ok",
            "data": results,
            "meta": {
                "count": len(results),
                "customer_id": cid,
                "date_range": date_range,
                "ad_group_id": ad_group_id or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance de ad groups: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a performance dos grupos de anúncios.",
            "details": format_api_error(e),
        }
