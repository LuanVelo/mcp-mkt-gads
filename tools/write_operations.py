"""Tools de escrita (write operations) para Google Ads.

⚠️ Toda write operation exige confirm=True para executar.
   Com confirm=False retorna um preview da ação sem modificar nada.
"""

import logging

from auth.token_manager import get_client, get_customer_id
from utils.errors import format_api_error
from utils.formatters import micros_to_brl

logger = logging.getLogger(__name__)

BRL_TO_MICROS = 1_000_000


def pause_campaign(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    confirm: bool = False,
) -> dict:
    """Pausa uma campanha ativa.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha a ser pausada. Obrigatório.
        confirm: Se False, retorna preview sem executar. Se True, executa a ação.

    Returns:
        Dict com status, preview ou resultado da operação.
    """
    if not campaign_id:
        return {
            "status": "error",
            "error": "campaign_id é obrigatório para pausar uma campanha.",
        }

    cid = get_customer_id(customer_id)

    if not confirm:
        return {
            "status": "preview",
            "action": "pause_campaign",
            "message": f"⚠️ Esta ação IRÁ PAUSAR a campanha ID {campaign_id} na conta {cid}.",
            "instructions": "Para confirmar, chame novamente com confirm=True.",
        }

    try:
        client = get_client(customer_id)
        campaign_service = client.get_service("CampaignService")

        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.update
        campaign.resource_name = campaign_service.campaign_path(cid, campaign_id)
        campaign.status = client.enums.CampaignStatusEnum.PAUSED

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("status")
        campaign_operation.update_mask.CopyFrom(field_mask)

        response = campaign_service.mutate_campaigns(
            customer_id=cid, operations=[campaign_operation]
        )

        updated = response.results[0].resource_name
        logger.info("Campanha pausada: %s", updated)

        return {
            "status": "ok",
            "action": "pause_campaign",
            "message": f"Campanha ID {campaign_id} pausada com sucesso.",
            "resource_name": updated,
            "meta": {"customer_id": cid, "campaign_id": campaign_id},
        }

    except Exception as e:
        logger.error("Erro ao pausar campanha %s: %s", campaign_id, e)
        return {
            "status": "error",
            "error": "Não foi possível pausar a campanha.",
            "details": format_api_error(e),
        }


def enable_campaign(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    confirm: bool = False,
) -> dict:
    """Ativa (despausa) uma campanha.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha a ser ativada. Obrigatório.
        confirm: Se False, retorna preview sem executar. Se True, executa a ação.

    Returns:
        Dict com status, preview ou resultado da operação.
    """
    if not campaign_id:
        return {
            "status": "error",
            "error": "campaign_id é obrigatório para ativar uma campanha.",
        }

    cid = get_customer_id(customer_id)

    if not confirm:
        return {
            "status": "preview",
            "action": "enable_campaign",
            "message": f"⚠️ Esta ação IRÁ ATIVAR a campanha ID {campaign_id} na conta {cid}.",
            "instructions": "Para confirmar, chame novamente com confirm=True.",
        }

    try:
        client = get_client(customer_id)
        campaign_service = client.get_service("CampaignService")

        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.update
        campaign.resource_name = campaign_service.campaign_path(cid, campaign_id)
        campaign.status = client.enums.CampaignStatusEnum.ENABLED

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("status")
        campaign_operation.update_mask.CopyFrom(field_mask)

        response = campaign_service.mutate_campaigns(
            customer_id=cid, operations=[campaign_operation]
        )

        updated = response.results[0].resource_name
        logger.info("Campanha ativada: %s", updated)

        return {
            "status": "ok",
            "action": "enable_campaign",
            "message": f"Campanha ID {campaign_id} ativada com sucesso.",
            "resource_name": updated,
            "meta": {"customer_id": cid, "campaign_id": campaign_id},
        }

    except Exception as e:
        logger.error("Erro ao ativar campanha %s: %s", campaign_id, e)
        return {
            "status": "error",
            "error": "Não foi possível ativar a campanha.",
            "details": format_api_error(e),
        }


def update_campaign_budget(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    new_budget_brl: float | None = None,
    confirm: bool = False,
) -> dict:
    """Atualiza o orçamento diário de uma campanha.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha. Obrigatório.
        new_budget_brl: Novo orçamento diário em BRL (ex: 50.00). Obrigatório.
        confirm: Se False, retorna preview sem executar. Se True, executa a ação.

    Returns:
        Dict com status, preview ou resultado da operação.
    """
    if not campaign_id:
        return {
            "status": "error",
            "error": "campaign_id é obrigatório para atualizar o budget.",
        }

    if new_budget_brl is None or new_budget_brl <= 0:
        return {
            "status": "error",
            "error": "new_budget_brl deve ser um valor positivo em BRL.",
        }

    cid = get_customer_id(customer_id)
    new_budget_micros = int(new_budget_brl * BRL_TO_MICROS)

    if not confirm:
        return {
            "status": "preview",
            "action": "update_campaign_budget",
            "message": (
                f"⚠️ Esta ação IRÁ ATUALIZAR o budget da campanha ID {campaign_id} "
                f"na conta {cid} para R$ {new_budget_brl:.2f}/dia."
            ),
            "new_budget_brl": new_budget_brl,
            "new_budget_micros": new_budget_micros,
            "instructions": "Para confirmar, chame novamente com confirm=True.",
        }

    try:
        client = get_client(customer_id)
        ga_service = client.get_service("GoogleAdsService")

        # Busca o resource_name do budget vinculado à campanha
        query = f"""
            SELECT
                campaign.id,
                campaign_budget.resource_name,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.id = {campaign_id}
            LIMIT 1
        """
        response = ga_service.search(customer_id=cid, query=query)
        row = next(iter(response), None)

        if row is None:
            return {
                "status": "error",
                "error": f"Campanha ID {campaign_id} não encontrada na conta {cid}.",
            }

        old_budget_brl = micros_to_brl(row.campaign_budget.amount_micros)
        budget_resource_name = row.campaign_budget.resource_name

        budget_service = client.get_service("CampaignBudgetService")
        budget_operation = client.get_type("CampaignBudgetOperation")
        budget = budget_operation.update
        budget.resource_name = budget_resource_name
        budget.amount_micros = new_budget_micros

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        budget_operation.update_mask.CopyFrom(field_mask)

        budget_service.mutate_campaign_budgets(
            customer_id=cid, operations=[budget_operation]
        )

        logger.info(
            "Budget da campanha %s atualizado: R$ %.2f → R$ %.2f",
            campaign_id, old_budget_brl, new_budget_brl,
        )

        return {
            "status": "ok",
            "action": "update_campaign_budget",
            "message": (
                f"Budget da campanha ID {campaign_id} atualizado de "
                f"R$ {old_budget_brl:.2f} para R$ {new_budget_brl:.2f}/dia."
            ),
            "old_budget_brl": old_budget_brl,
            "new_budget_brl": new_budget_brl,
            "meta": {"customer_id": cid, "campaign_id": campaign_id},
        }

    except Exception as e:
        logger.error("Erro ao atualizar budget da campanha %s: %s", campaign_id, e)
        return {
            "status": "error",
            "error": "Não foi possível atualizar o budget da campanha.",
            "details": format_api_error(e),
        }


def pause_keyword(
    customer_id: str | None = None,
    criterion_id: str | None = None,
    ad_group_id: str | None = None,
    confirm: bool = False,
) -> dict:
    """Pausa uma palavra-chave em um grupo de anúncios.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        criterion_id: ID do critério (keyword). Obrigatório.
        ad_group_id: ID do ad group que contém a keyword. Obrigatório.
        confirm: Se False, retorna preview sem executar. Se True, executa a ação.

    Returns:
        Dict com status, preview ou resultado da operação.
    """
    if not criterion_id or not ad_group_id:
        return {
            "status": "error",
            "error": "criterion_id e ad_group_id são obrigatórios para pausar uma keyword.",
        }

    cid = get_customer_id(customer_id)

    if not confirm:
        return {
            "status": "preview",
            "action": "pause_keyword",
            "message": (
                f"⚠️ Esta ação IRÁ PAUSAR a keyword (criterion_id={criterion_id}) "
                f"no ad group ID {ad_group_id}, conta {cid}."
            ),
            "instructions": "Para confirmar, chame novamente com confirm=True.",
        }

    try:
        client = get_client(customer_id)
        ag_criterion_service = client.get_service("AdGroupCriterionService")

        criterion_operation = client.get_type("AdGroupCriterionOperation")
        criterion = criterion_operation.update
        criterion.resource_name = ag_criterion_service.ad_group_criterion_path(
            cid, ad_group_id, criterion_id
        )
        criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED

        field_mask = client.get_type("FieldMask")
        field_mask.paths.append("status")
        criterion_operation.update_mask.CopyFrom(field_mask)

        response = ag_criterion_service.mutate_ad_group_criteria(
            customer_id=cid, operations=[criterion_operation]
        )

        updated = response.results[0].resource_name
        logger.info("Keyword pausada: %s", updated)

        return {
            "status": "ok",
            "action": "pause_keyword",
            "message": f"Keyword criterion_id={criterion_id} pausada com sucesso no ad group {ad_group_id}.",
            "resource_name": updated,
            "meta": {
                "customer_id": cid,
                "ad_group_id": ad_group_id,
                "criterion_id": criterion_id,
            },
        }

    except Exception as e:
        logger.error(
            "Erro ao pausar keyword criterion_id=%s ad_group_id=%s: %s",
            criterion_id, ad_group_id, e,
        )
        return {
            "status": "error",
            "error": "Não foi possível pausar a keyword.",
            "details": format_api_error(e),
        }


def add_negative_keyword(
    customer_id: str | None = None,
    campaign_id: str | None = None,
    keyword_text: str | None = None,
    match_type: str = "BROAD",
    confirm: bool = False,
) -> dict:
    """Adiciona uma keyword negativa em nível de campanha.

    Args:
        customer_id: Customer ID da conta. Se omitido, usa o do config.json.
        campaign_id: ID da campanha onde a negativa será adicionada. Obrigatório.
        keyword_text: Texto da keyword negativa (ex: "grátis", "de graça"). Obrigatório.
        match_type: Tipo de correspondência: "BROAD", "PHRASE" ou "EXACT". Default: "BROAD".
        confirm: Se False, retorna preview sem executar. Se True, executa a ação.

    Returns:
        Dict com status, preview ou resultado da operação.
    """
    if not campaign_id or not keyword_text:
        return {
            "status": "error",
            "error": "campaign_id e keyword_text são obrigatórios para adicionar keyword negativa.",
        }

    match_type = match_type.upper()
    valid_match_types = {"BROAD", "PHRASE", "EXACT"}
    if match_type not in valid_match_types:
        return {
            "status": "error",
            "error": f"match_type inválido: '{match_type}'. Use: BROAD, PHRASE ou EXACT.",
        }

    cid = get_customer_id(customer_id)

    match_type_display = {
        "BROAD": keyword_text,
        "PHRASE": f'"{keyword_text}"',
        "EXACT": f"[{keyword_text}]",
    }

    if not confirm:
        return {
            "status": "preview",
            "action": "add_negative_keyword",
            "message": (
                f"⚠️ Esta ação IRÁ ADICIONAR a keyword negativa "
                f"{match_type_display[match_type]} na campanha ID {campaign_id}, conta {cid}."
            ),
            "keyword_text": keyword_text,
            "match_type": match_type,
            "campaign_id": campaign_id,
            "instructions": "Para confirmar, chame novamente com confirm=True.",
        }

    try:
        client = get_client(customer_id)
        campaign_criterion_service = client.get_service("CampaignCriterionService")
        campaign_service = client.get_service("CampaignService")

        criterion_operation = client.get_type("CampaignCriterionOperation")
        criterion = criterion_operation.create
        criterion.campaign = campaign_service.campaign_path(cid, campaign_id)
        criterion.negative = True
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = getattr(
            client.enums.KeywordMatchTypeEnum, match_type
        )

        response = campaign_criterion_service.mutate_campaign_criteria(
            customer_id=cid, operations=[criterion_operation]
        )

        created = response.results[0].resource_name
        logger.info(
            "Keyword negativa adicionada na campanha %s: %s (%s)",
            campaign_id, keyword_text, match_type,
        )

        return {
            "status": "ok",
            "action": "add_negative_keyword",
            "message": (
                f"Keyword negativa {match_type_display[match_type]} adicionada "
                f"com sucesso na campanha ID {campaign_id}."
            ),
            "resource_name": created,
            "meta": {
                "customer_id": cid,
                "campaign_id": campaign_id,
                "keyword_text": keyword_text,
                "match_type": match_type,
            },
        }

    except Exception as e:
        logger.error(
            "Erro ao adicionar keyword negativa '%s' na campanha %s: %s",
            keyword_text, campaign_id, e,
        )
        return {
            "status": "error",
            "error": "Não foi possível adicionar a keyword negativa.",
            "details": format_api_error(e),
        }
