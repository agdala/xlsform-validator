"""Regras de listas de opções (OPC)."""

from __future__ import annotations

import re

from ..engine import Finding, rule
from ..form import CHOICES, SURVEY, Form, to_snake_case

TRUTHY = {"yes", "sim", "true", "1", "true()"}


@rule("OPC-01")
def lists_exist(form: Form, params: dict) -> list[Finding]:
    lists = form.choice_lists()
    out = []
    for row in form.select_questions():
        if row.list_name not in lists:
            out.append(
                Finding(
                    f"A pergunta '{row.name}' usa a lista '{row.list_name}', que não existe na aba 'choices'.",
                    sheet=SURVEY,
                    row=row.number,
                    suggestion="Crie a lista na aba 'choices' ou corrija o nome dela na coluna type.",
                )
            )
    return out


@rule("OPC-02")
def no_duplicate_choices(form: Form, params: dict) -> list[Finding]:
    if form.settings.get("allow_choice_duplicates", "").lower() in TRUTHY:
        return []
    out = []
    for list_name, rows in form.choice_lists().items():
        seen: dict[str, int] = {}
        for row in rows:
            name = row.name
            if not name:
                continue
            if name in seen:
                out.append(
                    Finding(
                        f"A opção '{name}' aparece duas vezes na lista '{list_name}' (primeira vez na linha {seen[name]}).",
                        sheet=CHOICES,
                        row=row.number,
                        suggestion="Dê um código diferente para cada opção da lista.",
                    )
                )
            else:
                seen[name] = row.number
    return out


@rule("OPC-03")
def no_orphan_lists(form: Form, params: dict) -> list[Finding]:
    used = {row.list_name for row in form.select_questions()}
    out = []
    for list_name, rows in form.choice_lists().items():
        if list_name not in used:
            out.append(
                Finding(
                    f"A lista '{list_name}' está definida, mas nenhuma pergunta a usa.",
                    sheet=CHOICES,
                    row=rows[0].number,
                    suggestion="Remova a lista ou confira se alguma pergunta deveria usá-la.",
                )
            )
    return out


def _multiple_lists(form: Form) -> dict[str, list]:
    result: dict[str, list] = {}
    for row in form.select_questions():
        if row.base_type == "select_multiple":
            result.setdefault(row.list_name, []).append(row)
    return result


@rule("OPC-04")
def no_spaces_in_multiple_codes(form: Form, params: dict) -> list[Finding]:
    lists = form.choice_lists()
    out = []
    for list_name in _multiple_lists(form):
        for row in lists.get(list_name, []):
            name = row.name
            if name and re.search(r"\s", name):
                out.append(
                    Finding(
                        f"O código '{name}' da lista '{list_name}' tem espaço. Em select_multiple o espaço "
                        "separa as respostas marcadas, então o código precisa ser uma palavra só. "
                        "O label pode ter quantas palavras quiser.",
                        sheet=CHOICES,
                        row=row.number,
                        suggestion=f"Sugestão de código: {to_snake_case(name)}",
                    )
                )
    return out


@rule("OPC-05")
def exclusive_option(form: Form, params: dict) -> list[Finding]:
    patterns = [re.compile(p) for p in params.get("padroes_exclusivos", [])]
    lists = form.choice_lists()
    out = []
    for list_name, questions in _multiple_lists(form).items():
        exclusive = [
            r.name for r in lists.get(list_name, []) if r.name and any(p.search(r.name) for p in patterns)
        ]
        for code in exclusive:
            for q in questions:
                constraint = q.get("constraint")
                if re.search(rf"['\"]{re.escape(code)}['\"]", constraint):
                    continue
                out.append(
                    Finding(
                        f"A pergunta '{q.name}' permite marcar '{code}' junto com outras opções.",
                        sheet=SURVEY,
                        row=q.number,
                        suggestion=(
                            f"constraint: not(selected(., '{code}') and count-selected(.) > 1)"
                        ),
                    )
                )
    return out
