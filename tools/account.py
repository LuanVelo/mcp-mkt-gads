"""Tools de visão geral da conta Google Ads."""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import format_status

logger = logging.getLogger(__name__)


def get_account_summary(customer_id: str | None = None) -> dict:
    """Retorna resumo da conta Google Ads: nome, moeda, fuso horário e status.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.

    Returns:
        Dict com status, data (resumo da conta) e meta.
    """
    try:
        client = get_client(customer_id)
        cid = get_customer_id(customer_id)

        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone,
                customer.status,
                customer.manager,
                customer.test_account
            FROM customer
            LIMIT 1
        """

        response = ga_service.search(customer_id=cid, query=query)
        rows = list(response)

        if not rows:
            return {
                "status": "error",
                "error": "Nenhuma informação de conta encontrada.",
                "details": "",
            }

        row = rows[0]
        c = row.customer

        return {
            "status": "ok",
            "data": {
                "id": str(c.id),
                "name": c.descriptive_name,
                "currency": c.currency_code,
                "timezone": c.time_zone,
                "status": format_status(c.status),
                "is_manager": c.manager,
                "is_test_account": c.test_account,
            },
            "meta": {"customer_id": cid},
        }

    except Exception as e:
        logger.error("Erro ao buscar resumo da conta: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível obter o resumo da conta.",
            "details": format_api_error(e),
        }


def list_accessible_customers() -> dict:
    """Lista todas as contas acessíveis com as credenciais configuradas.

    Útil para descobrir os Customer IDs disponíveis na MCC.

    Returns:
        Dict com status, data (lista de contas) e meta.
    """
    try:
        client = get_client()
        customer_service = client.get_service("CustomerService")

        accessible = customer_service.list_accessible_customers()
        resource_names = list(accessible.resource_names)

        customers = []
        for resource_name in resource_names:
            # resource_name é no formato "customers/XXXXXXXXXX"
            cid = resource_name.split("/")[-1]
            customers.append({"resource_name": resource_name, "customer_id": cid})

        return {
            "status": "ok",
            "data": customers,
            "meta": {"count": len(customers)},
        }

    except Exception as e:
        logger.error("Erro ao listar contas acessíveis: %s", e)
        return {
            "status": "error",
            "error": "Não foi possível listar as contas acessíveis.",
            "details": format_api_error(e),
        }
