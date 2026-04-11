"""Helpers para montar queries GAQL (Google Ads Query Language)."""

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

PRESET_DATE_RANGES = {
    "LAST_7_DAYS",
    "LAST_14_DAYS",
    "LAST_30_DAYS",
    "LAST_90_DAYS",
    "THIS_MONTH",
    "LAST_MONTH",
    "THIS_WEEK_SUN_TODAY",
    "THIS_WEEK_MON_TODAY",
    "LAST_WEEK_SUN_SAT",
    "LAST_WEEK_MON_SUN",
    "TODAY",
    "YESTERDAY",
}


def build_date_filter(date_range: str) -> str:
    """Converte um date_range para cláusula WHERE do GAQL.

    Aceita:
    - Presets padrão da API: "LAST_7_DAYS", "LAST_30_DAYS", "THIS_MONTH", etc.
    - Intervalo customizado: "YYYY-MM-DD,YYYY-MM-DD"

    Args:
        date_range: String com o intervalo de datas.

    Returns:
        Cláusula WHERE GAQL (ex: "segments.date DURING LAST_30_DAYS" ou
        "segments.date BETWEEN '2024-01-01' AND '2024-01-31'").

    Raises:
        ValueError: Se o formato não for reconhecido.
    """
    if not date_range:
        return "segments.date DURING LAST_30_DAYS"

    date_range = date_range.strip().upper()

    if date_range in PRESET_DATE_RANGES:
        return f"segments.date DURING {date_range}"

    # Tenta parse do formato customizado (case-insensitive, original case para datas)
    date_range_original = date_range.strip()
    if "," in date_range_original:
        parts = date_range_original.split(",")
        if len(parts) == 2:
            start = parts[0].strip()
            end = parts[1].strip()
            _validate_date_format(start)
            _validate_date_format(end)
            return f"segments.date BETWEEN '{start}' AND '{end}'"

    raise ValueError(
        f"Formato de date_range inválido: '{date_range}'. "
        "Use presets como 'LAST_30_DAYS' ou intervalo 'YYYY-MM-DD,YYYY-MM-DD'."
    )


def _validate_date_format(date_str: str) -> None:
    """Valida que a string está no formato YYYY-MM-DD.

    Args:
        date_str: String de data a validar.

    Raises:
        ValueError: Se o formato for inválido.
    """
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(
            f"Data inválida: '{date_str}'. Use o formato YYYY-MM-DD."
        )


def add_date_filter_to_query(query: str, date_range: str) -> str:
    """Adiciona ou substitui o filtro de data em uma query GAQL existente.

    Se a query já tem WHERE, adiciona AND. Se não tem, adiciona WHERE.

    Args:
        query: Query GAQL base (sem filtro de data).
        date_range: String com o intervalo de datas.

    Returns:
        Query com filtro de data inserido.
    """
    date_filter = build_date_filter(date_range)
    query = query.strip()

    if "WHERE" in query.upper():
        return f"{query} AND {date_filter}"
    else:
        return f"{query} WHERE {date_filter}"


def normalize_customer_id(customer_id: str) -> str:
    """Remove hífens e espaços do customer_id.

    Args:
        customer_id: Customer ID no formato xxx-xxx-xxxx ou xxxxxxxxxx.

    Returns:
        Customer ID apenas com dígitos.
    """
    return str(customer_id).replace("-", "").replace(" ", "").strip()
