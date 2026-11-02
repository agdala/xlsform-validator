"""Tradução das mensagens mais comuns do pyxform para português simples.

O pyxform só emite mensagens em inglês e com vocabulário técnico. Para quem monta
formulários no dia a dia, uma mensagem clara em português é o que permite corrigir
sem ajuda. Mensagens não reconhecidas são mantidas no original.
"""

from __future__ import annotations

import re

# (padrão, tradução). Os grupos nomeados do padrão podem ser usados na tradução.
TRANSLATIONS: list[tuple[str, str]] = [
    (
        r"the 'name' value '(?P<v>[^']+)' is invalid\. Questions, groups, and repeats must be unique",
        "O nome '{v}' está repetido. Perguntas, grupos e repetições precisam de nomes únicos.",
    ),
    (
        r"the 'name' value '(?P<v>[^']+)' is problematic\. The name is a case-insensitive match",
        "O nome '{v}' só difere de outro nome por letras maiúsculas ou minúsculas. Isso confunde a análise dos dados.",
    ),
    (
        r"On the 'choices' sheet, the 'name' value is invalid\. Choice names must be unique",
        "Há duas opções com o mesmo código (coluna name) na mesma lista da aba 'choices'.",
    ),
    (
        r"On the 'choices' sheet, the 'name' value is invalid\. Choices must have a name",
        "Há uma opção sem código (coluna name vazia) na aba 'choices'.",
    ),
    (
        r"On the 'choices' sheet, the 'label' value is invalid\. Choices should have a label",
        "Há uma opção sem texto (coluna label vazia) na aba 'choices'.",
    ),
    (
        r"On the '(?P<s>\w+)' sheet, the '(?P<c>[^']+)' value is invalid\. Names must begin with a letter or underscore",
        "Na aba '{s}', o valor da coluna '{c}' não é um nome válido: precisa começar com letra ou '_' e "
        "conter só letras, números, '_', '-' ou '.'.",
    ),
    (
        r"On the '(?P<s>\w+)' sheet, the '(?P<c>[^']+)' value is invalid\. Reference variables must contain a name from the 'survey' sheet\. Could not find the name '(?P<v>[^']+)'",
        "Na aba '{s}', a coluna '{c}' cita ${{{v}}}, mas essa pergunta não existe.",
    ),
    (
        r"On the '(?P<s>\w+)' sheet, the '(?P<c>[^']+)' value is invalid\. Reference variables must start with",
        "Na aba '{s}', a coluna '{c}' tem uma referência mal escrita. Use o formato ${{nome_da_pergunta}}.",
    ),
    (
        r"Unmatched 'end_(?P<t>group|repeat)'\. No matching 'begin_\w+' was found for the name '(?P<v>[^']*)'",
        "Há um 'end_{t}' ('{v}') sem o 'begin_{t}' correspondente.",
    ),
    (
        r"Unmatched 'begin_(?P<t>group|repeat)'\. No matching 'end_\w+' was found for the name '(?P<v>[^']*)'",
        "O grupo '{v}' foi aberto com 'begin_{t}', mas não foi fechado com 'end_{t}'.",
    ),
    (
        r"Unknown question type '(?P<v>[^']+)'",
        "O tipo de pergunta '{v}' não existe no XLSForm. Confira a ortografia (ex.: integer, text, select_one lista).",
    ),
    (
        r"List name not in choices sheet: (?P<v>\S+)",
        "A lista '{v}' é usada na aba 'survey', mas não existe na aba 'choices'.",
    ),
    (
        r"Choice names with spaces cannot be added to multiple choice selects\. See \[(?P<v>[^\]]+)\] in \[(?P<l>[^\]]+)\]",
        "O código '{v}' da lista '{l}' tem espaço e é usado em select_multiple. Troque os espaços por '_'.",
    ),
    (
        r"Invalid headers provided for sheet: '(?P<s>\w+)'\. One or more required column headers were not found: (?P<v>.+?)\. Learn more",
        "A aba '{s}' não tem colunas obrigatórias: {v}.",
    ),
    (
        r"When looking for a sheet named '(?P<s>\w+)', the following sheets with similar names were found: (?P<v>.+?)\.",
        "Não foi encontrada a aba '{s}', mas existem abas com nome parecido: {v}. O nome precisa ser exatamente '{s}'.",
    ),
    (
        r"The survey sheet is either empty or missing important column headers",
        "A aba 'survey' está vazia ou sem as colunas obrigatórias (type, name, label).",
    ),
]

_COMPILED = [(re.compile(p), t) for p, t in TRANSLATIONS]


def translate(message: str) -> str | None:
    """Devolve a tradução da mensagem, ou None se ela não for reconhecida."""
    for pattern, template in _COMPILED:
        match = pattern.search(message)
        if match:
            return template.format(**match.groupdict())
    return None
