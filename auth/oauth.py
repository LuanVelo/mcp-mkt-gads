"""Fluxo OAuth2 Google para autenticação com a Google Ads API."""

import logging
from typing import Optional

from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = "http://localhost:5001/oauth/callback"


def build_flow(client_id: str, client_secret: str) -> Flow:
    """Cria o objeto Flow do OAuth2 com as credenciais fornecidas.

    Args:
        client_id: Client ID do Google Cloud.
        client_secret: Client Secret do Google Cloud.

    Returns:
        Objeto Flow configurado.
    """
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    return flow


def get_authorization_url(client_id: str, client_secret: str) -> tuple[str, str]:
    """Gera a URL de autorização OAuth2 e o estado CSRF.

    Args:
        client_id: Client ID do Google Cloud.
        client_secret: Client Secret do Google Cloud.

    Returns:
        Tupla (authorization_url, state).
    """
    flow = build_flow(client_id, client_secret)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    logger.info("URL de autorização OAuth2 gerada.")
    return authorization_url, state


def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    authorization_response: str,
    state: Optional[str] = None,
) -> dict:
    """Troca o authorization code por access_token e refresh_token.

    Args:
        client_id: Client ID do Google Cloud.
        client_secret: Client Secret do Google Cloud.
        authorization_response: URL completa de callback recebida do Google.
        state: Estado CSRF (opcional, para validação).

    Returns:
        Dicionário com refresh_token, access_token e token_uri.

    Raises:
        ValueError: Se o exchange falhar ou o refresh_token não for retornado.
    """
    flow = build_flow(client_id, client_secret)

    if state:
        flow.state = state

    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials

    if not credentials.refresh_token:
        raise ValueError(
            "refresh_token não foi retornado pelo Google. "
            "Verifique se a conta já tinha autorização prévia — "
            "tente revogar o acesso em myaccount.google.com/permissions e tente novamente."
        )

    logger.info("Tokens OAuth2 obtidos com sucesso.")

    return {
        "refresh_token": credentials.refresh_token,
        "access_token": credentials.token,
        "token_uri": credentials.token_uri,
    }
