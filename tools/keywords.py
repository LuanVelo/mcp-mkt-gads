"""Tools de palavras-chave Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import (
    format_status,
    format_match_type,
    micros_to_brl,
    build_metrics_summary,
)
from utils.gaql import build_date_filter

logger = logging.getLogger(__name__)


def get_keywords(
    customer_id: str | None = None,
    ad_group_id: str | None = None,
    status: str | None = None,
) -> dict:
    """Lista palavras-chave com texto, match type, CPC, Quality Score e status.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        ad_group_id: ID do ad group para filtrar. Se omitido, retorna todas.
        status: Filtro de status: "ENABLED", "PAUSED", "REMOVED". Se omitido, retorna todas.

    Returns:
        Dict com status, data (lista de keywords) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.cpc_bid_micros,
                ad_group_criterion.quality_info.quality_score,
                ad_group_criterion.quality_info.search_predicted_ctr,
                ad_group_criterion.quality_info.creative_quality_score,
                ad_group_criterion.quality_info.post_click_quality_score,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = KEYWORD
        """

        conditions = []
        if ad_group_id:
            conditions.append(f"ad_group.id = {ad_group_id}")
        if status:
            conditions.append(f"ad_group_criterion.status = '{status.upper()}'")

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY ad_group_criterion.keyword.text"

        response = ga_service.search(customer_id=cid, query=query)
        keywords = []

        for row in response:
            kw = row.ad_group_criterion
            ag = row.ad_group
            c = row.campaign
            quality = kw.quality_info

            keywords.append({
                "criterion_id": str(kw.criterion_id),
                "text": kw.keyword.text,
                "match_type": format_match_type(kw.keyword.match_type),
                "status": format_status(kw.status),
                "max_cpc_brl": micros_to_brl(kw.cpc_bid_micros),
                "quality_score": quality.quality_score if quality.quality_score else None,
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "campaign_id": str(c.id),
                "campaign_name": c.name,
            })

        return {
            "status": "ok",
            "data": keywords,
            "meta": {
                "count": len(keywords),
                "customer_id": cid,
                "ad_group_id": ad_group_id or "ALL",
                "status_filter": status or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar keywords: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível listar as palavras-chave.",
            "details": format_api_error(e),
        }


def get_keyword_performance(
    customer_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str | None = None,
) -> dict:
    """Retorna métricas de performance por palavra-chave.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").
        campaign_id: ID da campanha para filtrar. Se omitido, retorna todas.

    Returns:
        Dict com status, data (lista de performance por keyword) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.average_cpc
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = KEYWORD
            AND {date_filter}
        """

        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"

        query += " ORDER BY metrics.cost_micros DESC"

        response = ga_service.search(customer_id=cid, query=query)
        results = []

        for row in response:
            kw = row.ad_group_criterion
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
                "criterion_id": str(kw.criterion_id),
                "keyword": kw.keyword.text,
                "match_type": format_match_type(kw.keyword.match_type),
                "status": format_status(kw.status),
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
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
                "campaign_id": campaign_id or "ALL",
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance de keywords: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a performance das palavras-chave.",
            "details": format_api_error(e),
        }
