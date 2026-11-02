"""Fixtures compartilhadas.

`base_form()` devolve um formulário mínimo que passa em TODAS as regras.
Cada teste altera só o necessário para provocar (ou não) a regra testada.
"""

from __future__ import annotations

import copy

import pytest

from xlsform_validator.engine import Finding, load_config, run_rules
from xlsform_validator.form import Form

BASE = {
    "survey": [
        {"type": "start", "name": "start"},
        {"type": "end", "name": "end"},
        {"type": "today", "name": "today"},
        {"type": "select_one sim_nao", "name": "consentimento", "label": "Aceita participar?"},
        {"type": "note", "name": "fim", "label": "Obrigado.", "relevant": "${consentimento} = 'nao'"},
        {"type": "begin_group", "name": "entrevista", "label": "Entrevista", "relevant": "${consentimento} = 'sim'"},
        {"type": "select_one sexo", "name": "sexo", "label": "Sexo"},
        {
            "type": "integer", "name": "idade", "label": "Idade",
            "constraint": ". >= 0 and . <= 120", "constraint_message": "Entre 0 e 120",
        },
        {
            "type": "calculate", "name": "faixa_etaria",
            "calculation": "if(${idade} < 18, '0_17', '18_mais')",
        },
        {
            "type": "date", "name": "data_chegada", "label": "Data de chegada",
            "constraint": ". <= today()", "constraint_message": "Não pode ser futura",
        },
        {"type": "end_group", "name": "entrevista"},
    ],
    "choices": [
        {"list_name": "sim_nao", "name": "sim", "label": "Sim"},
        {"list_name": "sim_nao", "name": "nao", "label": "Não"},
        {"list_name": "sexo", "name": "feminino", "label": "Feminino"},
        {"list_name": "sexo", "name": "masculino", "label": "Masculino"},
    ],
    "settings": [{"form_title": "Teste", "form_id": "teste", "version": "2026110201"}],
}


def base_dict() -> dict:
    return copy.deepcopy(BASE)


def make_form(data: dict | None = None) -> Form:
    return Form.from_dict(data if data is not None else base_dict())


def insert_in_group(data: dict, row: dict) -> dict:
    """Insere uma linha antes do end_group (dentro da parte com consentimento)."""
    data["survey"].insert(len(data["survey"]) - 1, row)
    return data


@pytest.fixture(scope="session")
def configs():
    cfgs = load_config()
    for c in cfgs:
        c.enabled = True if c.id != "TEC-03" else c.enabled
    return cfgs


@pytest.fixture
def check(configs):
    """check("NOM-01", form) -> lista de Findings só daquela regra."""

    def _check(rule_id: str, form: Form) -> list[Finding]:
        results = run_rules(form, configs, only={rule_id})
        assert results, f"Regra {rule_id} não executou"
        return results[0].findings

    return _check
