"""Regras de lógica (LOG), validações (VAL) e metadados (MET)."""

from __future__ import annotations

import difflib
import re

from ..engine import Finding, rule
from ..form import SETTINGS, SURVEY, Form, references

DEFAULT_LOGIC_COLUMNS = [
    "relevant", "constraint", "calculation", "choice_filter", "required",
    "repeat_count", "default", "label", "hint", "constraint_message",
]


@rule("LOG-01")
def references_exist(form: Form, params: dict) -> list[Finding]:
    columns = params.get("colunas", DEFAULT_LOGIC_COLUMNS)
    names = form.field_names()
    out = []

    def check(expression: str, column: str, sheet: str, row: int | None) -> None:
        for ref in references(expression):
            if ref in names:
                continue
            close = difflib.get_close_matches(ref, list(names), n=1)
            out.append(
                Finding(
                    f"A coluna '{column}' cita ${{{ref}}}, mas não existe pergunta com esse nome.",
                    sheet=sheet,
                    row=row,
                    column=column,
                    suggestion=f"Você quis dizer ${{{close[0]}}}?" if close else None,
                )
            )

    for row in form.survey:
        for column, value in row.data.items():
            if value and column.split("::", 1)[0] in columns:
                check(value, column, SURVEY, row.number)
    instance_name = form.settings.get("instance_name")
    if instance_name:
        check(instance_name, "instance_name", SETTINGS, 2)
    return out


@rule("LOG-02")
def constraint_has_message(form: Form, params: dict) -> list[Finding]:
    out = []
    for row in form.survey:
        if row.get("constraint") and not any(row.columns_starting("constraint_message").values()):
            out.append(
                Finding(
                    f"A pergunta '{row.name}' tem constraint, mas não tem constraint_message.",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion=f"Explique em linguagem simples a regra '{row.get('constraint')}', por exemplo: 'Informe um valor entre 0 e 20'.",
                )
            )
    return out


# ---------------------------------------------------------------- validações

NUMERIC = {"integer", "decimal"}
UPPER = re.compile(r"\.\s*<=?\s*(-?\d+(?:\.\d+)?)")
LOWER = re.compile(r"\.\s*>=?\s*(-?\d+(?:\.\d+)?)")


def _matches(name: str, patterns: list[str]) -> bool:
    return any(re.search(p, name) for p in patterns)


def _is_age(row, params: dict) -> bool:
    return row.base_type in NUMERIC and _matches(row.name, params.get("padroes_idade", []))


@rule("VAL-01")
def age_limits(form: Form, params: dict) -> list[Finding]:
    max_age = float(params.get("idade_maxima", 120))
    out = []
    for row in form.survey:
        if not _is_age(row, params):
            continue
        constraint = row.get("constraint")
        uppers = [float(x) for x in UPPER.findall(constraint)]
        lowers = [float(x) for x in LOWER.findall(constraint)]
        suggestion = f"constraint: . >= 0 and . <= {int(max_age)}"
        if not constraint:
            msg = f"O campo de idade '{row.name}' não tem constraint."
        elif not uppers or not lowers:
            msg = f"O campo de idade '{row.name}' não tem limite inferior e superior na constraint ('{constraint}')."
        elif max(uppers) > max_age:
            msg = f"O campo de idade '{row.name}' aceita até {max(uppers):g} anos (limite plausível: {max_age:g})."
        elif min(lowers) < 0:
            msg = f"O campo de idade '{row.name}' aceita valores negativos."
        else:
            continue
        out.append(Finding(msg, sheet=SURVEY, row=row.number, suggestion=suggestion))
    return out


@rule("VAL-02")
def dates_not_in_future(form: Form, params: dict) -> list[Finding]:
    types = set(params.get("tipos", ["date"]))
    exceptions = params.get("excecoes", [])
    pattern = re.compile(r"\.\s*<=?\s*(today|now)\(\)")
    out = []
    for row in form.survey:
        if row.base_type not in types or not row.name or _matches(row.name, exceptions):
            continue
        if pattern.search(row.get("constraint")):
            continue
        out.append(
            Finding(
                f"A data '{row.name}' aceita datas no futuro.",
                sheet=SURVEY,
                row=row.number,
                suggestion="constraint: . <= today()  (se a data puder ser futura, inclua o nome nas exceções da regra)",
            )
        )
    return out


@rule("VAL-03")
def numbers_have_limits(form: Form, params: dict) -> list[Finding]:
    # Campos de idade já são cobertos pela VAL-01, com limites próprios.
    ignore = params.get("ignorar_padroes", [])
    out = []
    for row in form.survey:
        if row.base_type not in NUMERIC or _matches(row.name, ignore):
            continue
        constraint = row.get("constraint")
        if UPPER.search(constraint) or LOWER.search(constraint):
            continue
        out.append(
            Finding(
                f"O campo numérico '{row.name}' não tem limite na constraint.",
                sheet=SURVEY,
                row=row.number,
                suggestion="Defina o intervalo plausível, por exemplo: . >= 1 and . <= 30",
            )
        )
    return out


# ---------------------------------------------------------------- metadados

@rule("MET-01")
def metadata_present(form: Form, params: dict) -> list[Finding]:
    present = {row.base_type for row in form.survey}
    return [
        Finding(
            f"O metadado '{meta}' não está no formulário.",
            sheet=SURVEY,
            suggestion=f"Adicione uma linha com type = {meta} e name = {meta}.",
        )
        for meta in params.get("obrigatorios", ["start", "end", "today"])
        if meta not in present
    ]
