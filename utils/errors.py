"""Utilitários para tratamento de erros da Google Ads API."""

import logging

logger = logging.getLogger(__name__)


def format_api_error(e: Exception) -> str:
    """Formata exceções da Google Ads API em mensagens legíveis.

    Para GoogleAdsException, extrai os erros detalhados do objeto failure,
    incluindo o código de erro e a mensagem de cada item.
    Para demais exceções, retorna str(e).

    Args:
        e: Exceção a formatar.

    Returns:
        String com mensagem de erro legível para exibição ao usuário.
    """
    try:
        from google.ads.googleads.errors import GoogleAdsException
        if isinstance(e, GoogleAdsException):
            messages = []
            for error in e.failure.errors:
                code_field = error.error_code.WhichOneof("error_code")
                if code_field:
                    code_value = getattr(error.error_code, code_field)
                    messages.append(f"[{code_field}:{code_value}] {error.message}")
                else:
                    messages.append(error.message or "Erro desconhecido")
            if messages:
                return "Google Ads API Error: " + " | ".join(messages)
            return f"Google Ads API Error: {str(e)}"
    except Exception:
        pass

    return str(e)
