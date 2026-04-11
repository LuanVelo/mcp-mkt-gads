"""Tools de termos de busca (search terms) Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import format_status, build_metrics_summary
from utils.gaql import build_date_filter

logger = logging.getLogger(__name__)


def get_search_terms(
    customer_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str | None = None,
) -> dict:
    """Retorna os termos de busca reais que ativaram anúncios.

    Útil para identificar termos irrelevantes e adicionar como negativos,
    ou descobrir novas oportunidades de palavras-chave.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").
        campaign_id: ID da campanha para filtrar. Se omitido, retorna todos.

    Returns:
        Dict com status, data (lista de search terms) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                search_term_view.search_term,
                search_term_view.status,
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM search_term_view
            WHERE {date_filter}
        """

        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"

        query += " ORDER BY metrics.impressions DESC"

        response = ga_service.search(customer_id=cid, query=query)
        results = []

        for row in response:
            stv = row.search_term_view
            c = row.campaign
            ag = row.ad_group
            m = row.metrics
            metrics = build_metrics_summary(
                impressions=m.impressions,
                clicks=m.clicks,
                cost_micros=m.cost_micros,
                conversions=m.conversions,
                conversion_value_micros=int(m.conversions_value * 1_000_000),
            )
            results.append({
                "search_term": stv.search_term,
                "status": format_status(stv.status),
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
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
        logger.error("Erro ao buscar search terms: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter os termos de busca.",
            "details": format_api_error(e),
        }
