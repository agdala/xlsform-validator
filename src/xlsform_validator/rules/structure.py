"""Regras de estrutura (EST)."""

from __future__ import annotations

import re

from ..engine import Finding, rule
from ..form import CHOICES, GROUP_BEGIN, GROUP_END, METADATA_TYPES, SETTINGS, SURVEY, Form


SETTINGS_HINTS = {
    "form_id": "Crie a coluna form_id com um identificador curto e estável, ex.: avaliacao_abrigo.",
    "version": "Crie a coluna version com a data e a revisão, ex.: 2026110201.",
}


def _misnamed(form: Form, sheet: str) -> str:
    found = form.misnamed_sheets.get(sheet)
    if found:
        return f" Existe uma aba chamada '{found}': o nome precisa ser exatamente '{sheet}', em minúsculas."
    return ""


def _needs_choices(form: Form) -> bool:
    return any(True for _ in form.select_questions())


@rule("EST-01")
def survey_and_choices_exist(form: Form, params: dict) -> list[Finding]:
    out = []
    if not form.has_sheet(SURVEY):
        out.append(Finding(f"A aba 'survey' não existe.{_misnamed(form, SURVEY)}"))
    if not form.has_sheet(CHOICES) and _needs_choices(form):
        out.append(
            Finding(
                "O formulário tem perguntas de múltipla escolha, mas a aba 'choices' não existe."
                + _misnamed(form, CHOICES)
            )
        )
    return out


@rule("EST-02")
def settings_exists(form: Form, params: dict) -> list[Finding]:
    if form.has_sheet(SETTINGS):
        return []
    return [
        Finding(
            "A aba 'settings' não existe." + _misnamed(form, SETTINGS),
            suggestion="Crie a aba 'settings' com as colunas form_title, form_id e version.",
        )
    ]


def _missing_columns(form: Form, sheet: str, required: list[str]) -> list[str]:
    headers = form.headers.get(sheet, [])
    missing = []
    for col in required:
        if col == "label":
            if not any(h == "label" or h.startswith("label::") for h in headers):
                missing.append("label (ou label::idioma)")
        elif col not in headers:
            missing.append(col)
    return missing


@rule("EST-03")
def survey_columns(form: Form, params: dict) -> list[Finding]:
    if not form.has_sheet(SURVEY):
        return []
    missing = _missing_columns(form, SURVEY, params.get("colunas", ["type", "name", "label"]))
    return [Finding(f"A aba 'survey' não tem a coluna obrigatória: {c}.", sheet=SURVEY, row=1) for c in missing]


@rule("EST-04")
def choices_columns(form: Form, params: dict) -> list[Finding]:
    if not form.has_sheet(CHOICES):
        return []
    missing = _missing_columns(form, CHOICES, params.get("colunas", ["list_name", "name", "label"]))
    return [Finding(f"A aba 'choices' não tem a coluna obrigatória: {c}.", sheet=CHOICES, row=1) for c in missing]


@rule("EST-05")
def settings_values(form: Form, params: dict) -> list[Finding]:
    if not form.has_sheet(SETTINGS):
        return []
    settings = form.settings
    out = []
    for col in params.get("campos", ["form_id", "version"]):
        if not settings.get(col):
            out.append(
                Finding(
                    f"O campo '{col}' não está preenchido na aba 'settings'.",
                    sheet=SETTINGS,
                    row=2,
                    suggestion=SETTINGS_HINTS.get(col),
                )
            )
    return out


@rule("EST-06")
def version_format(form: Form, params: dict) -> list[Finding]:
    version = form.settings.get("version", "")
    if not version:
        return []
    pattern = params.get("padrao", r"^\d{10}$")
    if re.fullmatch(pattern, version):
        return []
    return [
        Finding(
            f"A versão '{version}' não segue o padrão esperado ({params.get('exemplo', 'aaaammddrr')}).",
            sheet=SETTINGS,
            row=2,
            suggestion="Use a data da revisão seguida do número da revisão, por exemplo 2026110201.",
        )
    ]


@rule("EST-07")
def questions_have_label(form: Form, params: dict) -> list[Finding]:
    exempt = set(params.get("tipos_sem_label", [])) | METADATA_TYPES | GROUP_BEGIN | GROUP_END
    out = []
    for row in form.survey:
        base = row.base_type
        if not base or base in exempt:
            continue
        if not row.has_label():
            out.append(
                Finding(
                    f"A pergunta '{row.name or '(sem nome)'}' (tipo {base}) não tem label.",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion="Escreva o texto da pergunta exatamente como deve ser lido.",
                )
            )
    return out
