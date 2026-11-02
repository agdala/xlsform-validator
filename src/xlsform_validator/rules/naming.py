"""Regras de nomes de variáveis (NOM)."""

from __future__ import annotations

import re

from ..engine import Finding, rule
from ..form import SURVEY, Form, strip_accents, to_snake_case


@rule("NOM-01")
def unique_names(form: Form, params: dict) -> list[Finding]:
    seen: dict[str, int] = {}
    out = []
    for row in form.survey:
        name = row.name
        if not name:
            continue
        if name in seen:
            out.append(
                Finding(
                    f"O nome '{name}' já foi usado na linha {seen[name]}.",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion="Dê um nome diferente para cada pergunta.",
                )
            )
        else:
            seen[name] = row.number
    return out


@rule("NOM-02")
def snake_case(form: Form, params: dict) -> list[Finding]:
    pattern = params.get("padrao", r"^[a-z][a-z0-9_]*$")
    out = []
    for row in form.survey:
        name = row.name
        if not name:
            continue
        # Acentos são tratados pela NOM-03; aqui o nome é avaliado sem eles
        # para que o mesmo problema não apareça duas vezes.
        if re.fullmatch(pattern, strip_accents(name)):
            continue
        out.append(
            Finding(
                f"O nome '{name}' não está em snake_case (minúsculas, números e '_', começando por letra).",
                sheet=SURVEY,
                row=row.number,
                suggestion=f"Sugestão: {to_snake_case(name)}",
            )
        )
    return out


@rule("NOM-03")
def no_accents(form: Form, params: dict) -> list[Finding]:
    out = []
    for row in form.survey:
        name = row.name
        if name and not name.isascii():
            out.append(
                Finding(
                    f"O nome '{name}' tem acento, cedilha ou outro caractere especial.",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion=f"Sugestão: {to_snake_case(name)}",
                )
            )
    return out


@rule("NOM-04")
def max_length(form: Form, params: dict) -> list[Finding]:
    limit = int(params.get("tamanho_maximo", 32))
    out = []
    for row in form.survey:
        name = row.name
        if name and len(name) > limit:
            out.append(
                Finding(
                    f"O nome '{name}' tem {len(name)} caracteres (máximo: {limit}).",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion="Abrevie o nome mantendo o sentido; o texto completo fica no label.",
                )
            )
    return out
