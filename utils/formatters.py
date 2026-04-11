"""Formatters para converter e exibir dados da Google Ads API."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

MICROS_DIVISOR = 1_000_000


def micros_to_brl(micros: int | float) -> float:
    """Converte valor em micros para BRL.

    Args:
        micros: Valor em micros (ex: 1500000 = R$ 1,50).

    Returns:
        Valor em BRL com 2 casas decimais.
    """
    return round(micros / MICROS_DIVISOR, 2)


def format_ctr(impressions: int, clicks: int) -> str:
    """Calcula e formata o CTR como percentual.

    Args:
        impressions: Número de impressões.
        clicks: Número de cliques.

    Returns:
        CTR formatado como string (ex: "3.45%").
    """
    if impressions == 0:
        return "0.00%"
    ctr = (clicks / impressions) * 100
    return f"{ctr:.2f}%"


def format_roas(conversion_value_micros: int | float, cost_micros: int | float) -> str:
    """Calcula e formata o ROAS.

    Args:
        conversion_value_micros: Valor total das conversões em micros.
        cost_micros: Custo total em micros.

    Returns:
        ROAS formatado como string (ex: "4.20x") ou "N/A" se custo = 0.
    """
    if cost_micros == 0:
        return "N/A"
    roas = conversion_value_micros / cost_micros
    return f"{roas:.2f}x"


def format_cpa(cost_micros: int | float, conversions: float) -> str:
    """Calcula e formata o CPA (Custo por Aquisição) em BRL.

    Args:
        cost_micros: Custo total em micros.
        conversions: Número de conversões.

    Returns:
        CPA formatado como string (ex: "R$ 45.00") ou "N/A" se conversões = 0.
    """
    if conversions == 0:
        return "N/A"
    cpa = micros_to_brl(cost_micros) / conversions
    return f"R$ {cpa:.2f}"


def format_match_type(match_type_value: Any) -> str:
    """Converte o enum de match type para string legível.

    Args:
        match_type_value: Valor do enum KeywordMatchType.

    Returns:
        String legível do match type.
    """
    match_map = {
        0: "UNSPECIFIED",
        1: "UNKNOWN",
        2: "EXACT",
        3: "PHRASE",
        4: "BROAD",
    }
    if hasattr(match_type_value, "value"):
        return match_map.get(match_type_value.value, str(match_type_value))
    return match_map.get(int(match_type_value), str(match_type_value))


def format_status(status_value: Any) -> str:
    """Converte enum de status para string legível.

    Args:
        status_value: Valor do enum de status.

    Returns:
        String do nome do status.
    """
    if hasattr(status_value, "name"):
        return status_value.name
    return str(status_value)


def format_device(device_value: Any) -> str:
    """Converte enum de device para string legível.

    Args:
        device_value: Valor do enum Device.

    Returns:
        String legível do device.
    """
    device_map = {
        0: "UNSPECIFIED",
        1: "UNKNOWN",
        2: "MOBILE",
        3: "TABLET",
        4: "DESKTOP",
        5: "CONNECTED_TV",
        6: "OTHER",
    }
    if hasattr(device_value, "value"):
        return device_map.get(device_value.value, str(device_value))
    return device_map.get(int(device_value), str(device_value))


def format_campaign_type(campaign_type_value: Any) -> str:
    """Converte enum de tipo de campanha para string legível.

    Args:
        campaign_type_value: Valor do enum AdvertisingChannelType.

    Returns:
        String legível do tipo de campanha.
    """
    type_map = {
        0: "UNSPECIFIED",
        1: "UNKNOWN",
        2: "SEARCH",
        3: "DISPLAY",
        4: "SHOPPING",
        5: "HOTEL",
        6: "VIDEO",
        7: "MULTI_CHANNEL",
        8: "LOCAL",
        9: "SMART",
        10: "PERFORMANCE_MAX",
        11: "LOCAL_SERVICES",
        12: "DISCOVERY",
        13: "TRAVEL",
        14: "DEMAND_GEN",
    }
    if hasattr(campaign_type_value, "value"):
        return type_map.get(campaign_type_value.value, str(campaign_type_value))
    return type_map.get(int(campaign_type_value), str(campaign_type_value))


def build_metrics_summary(
    impressions: int,
    clicks: int,
    cost_micros: int | float,
    conversions: float = 0,
    conversion_value_micros: int | float = 0,
) -> dict:
    """Constrói um dict de métricas formatadas.

    Args:
        impressions: Número de impressões.
        clicks: Número de cliques.
        cost_micros: Custo em micros.
        conversions: Número de conversões (default 0).
        conversion_value_micros: Valor das conversões em micros (default 0).

    Returns:
        Dict com métricas formatadas prontas para retorno ao Claude.
    """
    return {
        "impressions": impressions,
        "clicks": clicks,
        "ctr": format_ctr(impressions, clicks),
        "cost_brl": micros_to_brl(cost_micros),
        "conversions": round(conversions, 2),
        "cpa": format_cpa(cost_micros, conversions),
        "roas": format_roas(conversion_value_micros, cost_micros),
    }
