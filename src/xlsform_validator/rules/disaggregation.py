"""Regras de desagregação (DES) e idiomas (IDI)."""

from __future__ import annotations

import re

from ..engine import Finding, rule
from ..form import CHOICES, SETTINGS, SURVEY, Form, references


def _find(form: Form, types: set[str], patterns: list[str]):
    return [
        r for r in form.survey
        if r.base_type in types and r.name and any(re.search(p, r.name) for p in patterns)
    ]


def _missing_codes(form: Form, list_name: str | None, expected: list[str]) -> list[str]:
    codes = {c.name for c in form.choice_lists().get(list_name or "", [])}
    return [str(code) for code in expected if str(code) not in codes]


@rule("DES-01")
def sex_question(form: Form, params: dict) -> list[Finding]:
    questions = _find(form, {"select_one"}, params.get("padroes_nome", []))
    expected = params.get("codigos_obrigatorios", [])
    if not questions:
        return [
            Finding(
                "Não há pergunta de sexo (select_one) para desagregar os resultados.",
                sheet=SURVEY,
                suggestion=f"Adicione type = select_one sexo, com os códigos: {', '.join(map(str, expected))}.",
            )
        ]
    out = []
    for q in questions:
        missing = _missing_codes(form, q.list_name, expected)
        if missing:
            out.append(
                Finding(
                    f"A lista '{q.list_name}' da pergunta '{q.name}' não segue o padrão: faltam os códigos {', '.join(missing)}.",
                    sheet=SURVEY,
                    row=q.number,
                    suggestion=f"Use a lista padrão com os códigos: {', '.join(map(str, expected))}.",
                )
            )
    return out


@rule("DES-02")
def age_group(form: Form, params: dict) -> list[Finding]:
    patterns = params.get("padroes_nome", [])
    expected = params.get("codigos_obrigatorios", [])
    selects = _find(form, {"select_one"}, patterns)
    calcs = _find(form, {"calculate"}, patterns)

    # Opção 1: faixa etária calculada a partir de uma idade numérica.
    numeric = {r.name for r in form.survey if r.base_type in ("integer", "decimal")}
    for calc in calcs:
        if set(references(calc.get("calculation"))) & numeric:
            return []

    # Opção 2: faixa etária perguntada diretamente, com lista padronizada.
    if selects:
        out = []
        for q in selects:
            missing = _missing_codes(form, q.list_name, expected)
            if missing:
                out.append(
                    Finding(
                        f"A lista '{q.list_name}' da pergunta '{q.name}' não segue as faixas padrão: faltam {', '.join(missing)}.",
                        sheet=SURVEY,
                        row=q.number,
                        suggestion=f"Use as faixas padrão: {', '.join(map(str, expected))}.",
                    )
                )
        return out

    return [
        Finding(
            "Não há faixa etária: nem pergunta com lista padronizada, nem calculate a partir da idade.",
            sheet=SURVEY,
            suggestion="Adicione um calculate 'faixa_etaria' a partir do campo de idade, nas faixas "
            + ", ".join(map(str, expected))
            + ".",
        )
    ]


# ---------------------------------------------------------------- idiomas

def _lang_col(base: str, lang: str) -> str:
    return f"{base}::{lang}" if lang else base


def _lang_label(lang: str) -> str:
    return lang or "label sem idioma"


def _check_translations(form: Form, bases: list[str]) -> list[Finding]:
    langs = form.languages()
    if len(langs) < 2:
        return []
    out = []
    for sheet in (SURVEY, CHOICES):
        for row in form.rows(sheet):
            for base in bases:
                values = {lang: row.get(_lang_col(base, lang)) for lang in langs}
                if not any(values.values()):
                    continue
                missing = [_lang_label(lang) for lang, v in values.items() if not v]
                if missing:
                    ident = row.name or row.get("type")
                    out.append(
                        Finding(
                            f"'{ident}': coluna {base} sem tradução para {', '.join(missing)}.",
                            sheet=sheet,
                            row=row.number,
                            suggestion=f"Preencha a coluna {base}::" + " e ".join(m for m in missing) + ".",
                        )
                    )
    return out


@rule("IDI-01")
def labels_translated(form: Form, params: dict) -> list[Finding]:
    return _check_translations(form, ["label"])


@rule("IDI-02")
def other_columns_translated(form: Form, params: dict) -> list[Finding]:
    return _check_translations(form, params.get("colunas", ["hint", "constraint_message"]))


@rule("IDI-03")
def default_language(form: Form, params: dict) -> list[Finding]:
    langs = [lang for lang in form.languages() if lang]
    if len(form.languages()) < 2 or form.settings.get("default_language"):
        return []
    return [
        Finding(
            "O formulário tem mais de um idioma, mas 'default_language' não está definido na aba 'settings'.",
            sheet=SETTINGS,
            row=2 if form.has_sheet(SETTINGS) else None,
            suggestion=f"Defina default_language, por exemplo: {langs[0] if langs else 'Português (pt)'}.",
        )
    ]
