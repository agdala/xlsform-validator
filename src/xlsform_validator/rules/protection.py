"""Regras de consentimento (CON) e proteção de dados / LGPD (LGPD)."""

from __future__ import annotations

import re

from ..engine import Finding, rule
from ..form import GROUP_BEGIN, GROUP_END, METADATA_TYPES, SURVEY, Form, Row, iter_tokens, references, strip_accents

NON_QUESTION = METADATA_TYPES | GROUP_BEGIN | GROUP_END | {"calculate", "hidden", "note", ""}


# ---------------------------------------------------------------- consentimento

def _consent_row(form: Form, params: dict) -> Row | None:
    patterns = params.get("padroes_nome", ["consent"])
    for row in form.survey:
        if row.base_type == "select_one" and any(re.search(p, row.name) for p in patterns):
            return row
    return None


@rule("CON-01")
def consent_exists(form: Form, params: dict) -> list[Finding]:
    if _consent_row(form, params):
        return []
    return [
        Finding(
            "Não há pergunta de consentimento (select_one com nome que indique consentimento).",
            sheet=SURVEY,
            suggestion="Adicione no início: type = select_one sim_nao, name = consentimento.",
        )
    ]


@rule("CON-02")
def consent_at_start(form: Form, params: dict) -> list[Finding]:
    consent = _consent_row(form, params)
    if not consent:
        return []
    max_pos = int(params.get("posicao_maxima", 3))
    questions = [r for r in form.survey if r.base_type not in NON_QUESTION]
    position = next(i for i, r in enumerate(questions, start=1) if r is consent)
    if position <= max_pos:
        return []
    return [
        Finding(
            f"A pergunta de consentimento '{consent.name}' é a pergunta nº {position}; "
            f"ela deve estar entre as {max_pos} primeiras.",
            sheet=SURVEY,
            row=consent.number,
            suggestion="Mova o consentimento para antes de qualquer pergunta de conteúdo.",
        )
    ]


@rule("CON-03")
def consent_ends_interview(form: Form, params: dict) -> list[Finding]:
    consent = _consent_row(form, params)
    if not consent:
        return []
    exempt = set(params.get("tipos_isentos", [])) | METADATA_TYPES | GROUP_END
    name = consent.name

    def gated(row: Row) -> bool:
        return name in references(row.get("relevant"))

    out = []
    after = False
    for row, groups in form.iter_with_groups():
        if row is consent:
            after = True
            continue
        if not after or row.base_type in exempt:
            continue
        if gated(row) or any(gated(g) for g in groups):
            continue
        # Um grupo sem condição não guarda dado; o problema é reportado nas
        # perguntas dentro dele, a menos que o próprio grupo seja condicionado.
        if row.base_type in GROUP_BEGIN:
            continue
        out.append(
            Finding(
                f"A pergunta '{row.name}' aparece mesmo se a pessoa não consentir.",
                sheet=SURVEY,
                row=row.number,
                suggestion=f"Coloque as perguntas em um grupo com relevant: ${{{name}}} = 'sim'.",
            )
        )
    return out


# ---------------------------------------------------------------- LGPD

def _flag(value: str) -> bool | None:
    value = strip_accents(value).strip().lower()
    if value in {"sim", "yes", "s", "true", "1"}:
        return True
    if value in {"nao", "no", "n", "false", "0"}:
        return False
    return None


def personal_data_fields(form: Form, params: dict) -> list[tuple[Row, str]]:
    """Campos com dado pessoal direto e o motivo da detecção."""
    keywords = set(params.get("palavras_nome", []))
    label_patterns = [re.compile(p) for p in params.get("padroes_label", [])]
    types = set(params.get("tipos", []))
    marker = params.get("coluna_marcacao", "dado_pessoal")
    found = []
    for row in form.survey:
        if not row.name or row.base_type in (GROUP_BEGIN | GROUP_END):
            continue
        explicit = _flag(row.get(marker))
        if explicit is False:
            continue
        reason = None
        if explicit:
            reason = f"marcado na coluna '{marker}'"
        elif row.base_type in types:
            reason = f"tipo {row.base_type}"
        else:
            hit = keywords.intersection(iter_tokens(row.name))
            if hit:
                reason = f"nome contém '{sorted(hit)[0]}'"
            else:
                labels = " ".join(row.columns_starting("label").values())
                label = strip_accents(labels).lower()
                for p in label_patterns:
                    if p.search(label):
                        reason = "label indica dado pessoal"
                        break
        if reason:
            found.append((row, reason))
    return found


@rule("LGPD-01")
def flag_personal_data(form: Form, params: dict) -> list[Finding]:
    marker = params.get("coluna_marcacao", "dado_pessoal")
    return [
        Finding(
            f"O campo '{row.name}' parece coletar dado pessoal direto ({reason}).",
            sheet=SURVEY,
            row=row.number,
            suggestion=f"Confirme na coluna '{marker}': 'sim' se for dado pessoal indispensável, 'nao' se for falso positivo.",
        )
        for row, reason in personal_data_fields(form, params)
        # Campos já confirmados pela equipe não precisam de novo alerta.
        if _flag(row.get(marker)) is not True
    ]


@rule("LGPD-02")
def personal_data_justified(form: Form, params: dict) -> list[Finding]:
    column = params.get("coluna_justificativa", "justificativa_dados_pessoais")
    out = []
    for row, _reason in personal_data_fields(form, params):
        if len(row.get(column)) >= int(params.get("tamanho_minimo", 15)):
            continue
        out.append(
            Finding(
                f"O campo '{row.name}' coleta dado pessoal sem justificativa documentada.",
                sheet=SURVEY,
                row=row.number,
                suggestion=f"Preencha a coluna '{column}' com a finalidade e a base legal (ex.: 'Contato para encaminhamento; consentimento').",
            )
        )
    return out


@rule("LGPD-03")
def sensitive_has_opt_out(form: Form, params: dict) -> list[Finding]:
    topics = [re.compile(p) for p in params.get("padroes_tema", [])]
    opt_out = [re.compile(p) for p in params.get("padroes_recusa", [])]
    lists = form.choice_lists()
    out = []
    for row in form.select_questions():
        text = strip_accents(" ".join([row.name, *row.columns_starting("label").values()])).lower()
        if not any(p.search(text) for p in topics):
            continue
        codes = [c.name for c in lists.get(row.list_name, [])]
        if any(p.search(code) for code in codes for p in opt_out):
            continue
        out.append(
            Finding(
                f"A pergunta '{row.name}' trata de tema sensível e não oferece a opção de não responder.",
                sheet=SURVEY,
                row=row.number,
                suggestion=f"Inclua na lista '{row.list_name}' a opção prefiro_nao_responder.",
            )
        )
    return out
