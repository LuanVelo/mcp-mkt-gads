"""Gerenciamento de tokens e instanciação do GoogleAdsClient."""

import logging
from typing import Optional

from google.ads.googleads.client import GoogleAdsClient
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from utils.config import load_config, save_config

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_credentials(config: dict) -> Credentials:
    """Constrói o objeto Credentials a partir do config.

    Args:
        config: Dicionário carregado do config.json.

    Returns:
        Objeto Credentials do google-auth.
    """
    return Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        token_uri=GOOGLE_TOKEN_URI,
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=["https://www.googleapis.com/auth/adwords"],
    )


def _refresh_if_needed(credentials: Credentials, config: dict) -> Credentials:
    """Faz refresh do access_token se estiver expirado ou ausente.

    Args:
        credentials: Objeto Credentials atual.
        config: Dicionário de configuração (para persistir novo token se necessário).

    Returns:
        Credentials atualizado.
    """
    if not credentials.valid:
        logger.info("Access token expirado ou ausente — fazendo refresh.")
        request = Request()
        credentials.refresh(request)
        logger.info("Access token renovado com sucesso.")

    return credentials


def _validate_config(config: dict) -> None:
    """Valida que os campos obrigatórios estão presentes no config.

    Args:
        config: Dicionário de configuração.

    Raises:
        ValueError: Se algum campo obrigatório estiver ausente.
    """
    required = ["client_id", "client_secret", "developer_token", "refresh_token", "customer_id"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise ValueError(
            f"Configuração incompleta. Campos faltando: {', '.join(missing)}. "
            "Execute o setup em http://localhost:5001 para configurar as credenciais."
        )


def get_client(customer_id: Optional[str] = None) -> GoogleAdsClient:
    """Retorna um GoogleAdsClient autenticado e pronto para uso.

    Carrega o config.json, valida os campos obrigatórios, faz refresh do
    token se necessário e instancia o cliente.

    Args:
        customer_id: Customer ID opcional para sobrescrever o do config.
                     Se não fornecido, usa o customer_id do config.json.

    Returns:
        GoogleAdsClient configurado e autenticado.

    Raises:
        ValueError: Se a configuração estiver incompleta ou o token inválido.
    """
    config = load_config()
    _validate_config(config)

    credentials = _build_credentials(config)
    credentials = _refresh_if_needed(credentials, config)

    effective_customer_id = _normalize_customer_id(
        customer_id or config["customer_id"]
    )

    client_config = {
        "developer_token": config["developer_token"],
        "refresh_token": config["refresh_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "use_proto_plus": config.get("use_proto_plus", True),
    }

    if config.get("login_customer_id"):
        client_config["login_customer_id"] = _normalize_customer_id(
            config["login_customer_id"]
        )

    logger.debug(
        "Instanciando GoogleAdsClient para customer_id=%s", effective_customer_id
    )

    client = GoogleAdsClient.load_from_dict(client_config)
    return client


def _normalize_customer_id(customer_id: str) -> str:
    """Remove hífens do customer_id para uso na API.

    Args:
        customer_id: Customer ID no formato xxx-xxx-xxxx ou xxxxxxxxxx.

    Returns:
        Customer ID apenas com dígitos.
    """
    return str(customer_id).replace("-", "").strip()


def get_customer_id(customer_id: Optional[str] = None) -> str:
    """Retorna o customer_id normalizado (sem hífens).

    Usa o parâmetro se fornecido, caso contrário lê do config.json.

    Args:
        customer_id: Customer ID opcional para sobrescrever o do config.

    Returns:
        Customer ID normalizado.
    """
    config = load_config()
    raw_id = customer_id or config.get("customer_id", "")
    return _normalize_customer_id(raw_id)
