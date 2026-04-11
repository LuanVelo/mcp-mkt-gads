import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "client_id": "",
    "client_secret": "",
    "developer_token": "",
    "refresh_token": "",
    "customer_id": "",
    "login_customer_id": "",
    "use_proto_plus": True,
    "test_account": False,
}


def load_config() -> dict[str, Any]:
    """Carrega o config.json do disco.

    Returns:
        dict com as configurações. Se o arquivo não existir, retorna o DEFAULT_CONFIG.

    Raises:
        ValueError: Se o arquivo existir mas não for um JSON válido.
    """
    if not os.path.exists(CONFIG_PATH):
        logger.warning("config.json não encontrado em %s. Retornando config padrão.", CONFIG_PATH)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.debug("config.json carregado de %s", CONFIG_PATH)
        return {**DEFAULT_CONFIG, **config}
    except json.JSONDecodeError as e:
        raise ValueError(f"config.json inválido: {e}") from e


def save_config(config: dict[str, Any]) -> None:
    """Salva o dicionário de configuração no config.json.

    Args:
        config: Dicionário com as configurações a serem salvas.

    Raises:
        OSError: Se não for possível escrever o arquivo.
    """
    merged = {**DEFAULT_CONFIG, **config}

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info("config.json salvo em %s", CONFIG_PATH)


def is_configured() -> bool:
    """Verifica se as credenciais mínimas estão preenchidas no config.json.

    Returns:
        True se client_id, client_secret, developer_token, refresh_token
        e customer_id estiverem preenchidos.
    """
    config = load_config()
    required = ["client_id", "client_secret", "developer_token", "refresh_token", "customer_id"]
    return all(bool(config.get(k)) for k in required)
