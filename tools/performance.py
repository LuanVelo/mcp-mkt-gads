"""Tools de performance e métricas agregadas da conta Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import format_device, build_metrics_summary, micros_to_brl
from utils.gaql import build_date_filter

logger = logging.getLogger(__name__)


def get_account_performance(
    customer_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Retorna visão geral de performance da conta com todas as métricas.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").

    Returns:
        Dict com status, data (métricas agregadas) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.average_cpc,
                metrics.ctr
            FROM customer
            WHERE {date_filter}
        """

        response = ga_service.search(customer_id=cid, query=query)
        rows = list(response)

        # Agrega totais (a query de customer já retorna totais)
        total_impressions = 0
        total_clicks = 0
        total_cost_micros = 0
        total_conversions = 0.0
        total_conversion_value = 0.0

        for row in rows:
            m = row.metrics
            total_impressions += m.impressions
            total_clicks += m.clicks
            total_cost_micros += m.cost_micros
            total_conversions += m.conversions
            total_conversion_value += m.conversions_value

        metrics = build_metrics_summary(
            impressions=total_impressions,
            clicks=total_clicks,
            cost_micros=total_cost_micros,
            conversions=total_conversions,
            conversion_value_micros=int(total_conversion_value * 1_000_000),
        )

        return {
            "status": "ok",
            "data": metrics,
            "meta": {
                "customer_id": cid,
                "date_range": date_range,
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance da conta: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a performance da conta.",
            "details": format_api_error(e),
        }


def get_performance_by_device(
    customer_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Retorna performance segmentada por dispositivo (mobile, desktop, tablet).

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").

    Returns:
        Dict com status, data (performance por device) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                segments.device,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE {date_filter}
        """

        response = ga_service.search(customer_id=cid, query=query)

        # Agrega por device
        device_data: dict = {}
        for row in response:
            device = format_device(row.segments.device)
            m = row.metrics

            if device not in device_data:
                device_data[device] = {
                    "impressions": 0,
                    "clicks": 0,
                    "cost_micros": 0,
                    "conversions": 0.0,
                    "conversion_value": 0.0,
                }

            device_data[device]["impressions"] += m.impressions
            device_data[device]["clicks"] += m.clicks
            device_data[device]["cost_micros"] += m.cost_micros
            device_data[device]["conversions"] += m.conversions
            device_data[device]["conversion_value"] += m.conversions_value

        results = []
        for device, d in device_data.items():
            metrics = build_metrics_summary(
                impressions=d["impressions"],
                clicks=d["clicks"],
                cost_micros=d["cost_micros"],
                conversions=d["conversions"],
                conversion_value_micros=int(d["conversion_value"] * 1_000_000),
            )
            results.append({"device": device, **metrics})

        # Ordena por custo decrescente
        results.sort(key=lambda x: x["cost_brl"], reverse=True)

        return {
            "status": "ok",
            "data": results,
            "meta": {
                "count": len(results),
                "customer_id": cid,
                "date_range": date_range,
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance por device: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a performance por dispositivo.",
            "details": format_api_error(e),
        }


def get_performance_by_day(
    customer_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Retorna série temporal diária de performance.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        date_range: Intervalo de datas ("LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH",
                    "LAST_MONTH" ou "YYYY-MM-DD,YYYY-MM-DD").

    Returns:
        Dict com status, data (lista diária de métricas) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        date_filter = build_date_filter(date_range)

        query = f"""
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM customer
            WHERE {date_filter}
            ORDER BY segments.date ASC
        """

        response = ga_service.search(customer_id=cid, query=query)
        results = []

        for row in response:
            m = row.metrics
            metrics = build_metrics_summary(
                impressions=m.impressions,
                clicks=m.clicks,
                cost_micros=m.cost_micros,
                conversions=m.conversions,
                conversion_value_micros=int(m.conversions_value * 1_000_000),
            )
            results.append({"date": row.segments.date, **metrics})

        return {
            "status": "ok",
            "data": results,
            "meta": {
                "count": len(results),
                "customer_id": cid,
                "date_range": date_range,
            },
        }

    except Exception as e:
        logger.error("Erro ao buscar performance por dia: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter a série temporal de performance.",
            "details": format_api_error(e),
        }
