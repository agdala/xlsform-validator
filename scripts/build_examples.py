"""Gera os formulários de exemplo (todos fictícios).

Tema: avaliação de necessidades de famílias em um abrigo temporário.
Nenhum dado, abrigo ou formulário real foi usado.

Uso:
    python scripts/build_examples.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
PT = "Português (pt)"
ES = "Español (es)"
L_PT, L_ES = f"label::{PT}", f"label::{ES}"
H_PT, H_ES = f"hint::{PT}", f"hint::{ES}"
M_PT, M_ES = f"constraint_message::{PT}", f"constraint_message::{ES}"


def save(path: Path, sheets: dict[str, tuple[list[str], list[dict]]]) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for name, (headers, rows) in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DDEBF7")
        for row in rows:
            ws.append([row.get(h) for h in headers])
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 60)
        ws.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    print(f"gerado: {path.relative_to(ROOT)}")


# ====================================================================== BOM

def good_form() -> dict:
    survey_headers = [
        "type", "name", L_PT, L_ES, H_PT, H_ES, "required", "relevant",
        "constraint", M_PT, M_ES, "calculation", "dado_pessoal", "justificativa_dados_pessoais",
    ]
    msg_data = ("A data não pode estar no futuro.", "La fecha no puede ser futura.")
    survey = [
        {"type": "start", "name": "start"},
        {"type": "end", "name": "end"},
        {"type": "today", "name": "today"},
        {"type": "deviceid", "name": "deviceid"},
        {
            "type": "note", "name": "apresentacao",
            L_PT: "Olá! Somos da equipe de apoio do abrigo. Esta entrevista é voluntária, leva cerca de 10 minutos e as respostas são confidenciais.",
            L_ES: "¡Hola! Somos del equipo de apoyo del albergue. Esta entrevista es voluntaria, dura unos 10 minutos y las respuestas son confidenciales.",
        },
        {
            "type": "select_one sim_nao", "name": "consentimento", "required": "yes",
            L_PT: "Você aceita participar desta entrevista?",
            L_ES: "¿Acepta participar en esta entrevista?",
        },
        {
            "type": "note", "name": "encerramento", "relevant": "${consentimento} = 'nao'",
            L_PT: "Obrigado pelo seu tempo. A entrevista termina aqui.",
            L_ES: "Gracias por su tiempo. La entrevista termina aquí.",
        },
        {
            "type": "begin_group", "name": "entrevista", "relevant": "${consentimento} = 'sim'",
            L_PT: "Avaliação de necessidades", L_ES: "Evaluación de necesidades",
        },
        {
            "type": "select_one abrigos", "name": "abrigo", "required": "yes",
            L_PT: "Em qual abrigo a família está?", L_ES: "¿En qué albergue está la familia?",
        },
        {
            "type": "date", "name": "data_chegada", "required": "yes",
            L_PT: "Em que data a família chegou ao abrigo?", L_ES: "¿En qué fecha llegó la familia al albergue?",
            H_PT: "Se não souber o dia exato, use uma data aproximada.",
            H_ES: "Si no sabe el día exacto, use una fecha aproximada.",
            "constraint": ". <= today()", M_PT: msg_data[0], M_ES: msg_data[1],
        },
        {
            "type": "select_one sexo", "name": "sexo_respondente", "required": "yes",
            L_PT: "Qual é o seu sexo?", L_ES: "¿Cuál es su sexo?",
        },
        {
            "type": "integer", "name": "idade_respondente", "required": "yes",
            L_PT: "Qual é a sua idade?", L_ES: "¿Cuál es su edad?",
            "constraint": ". >= 18 and . <= 120",
            M_PT: "Informe uma idade entre 18 e 120 anos.", M_ES: "Indique una edad entre 18 y 120 años.",
        },
        {
            "type": "calculate", "name": "faixa_etaria",
            "calculation": "if(${idade_respondente} < 5, '0_4', if(${idade_respondente} < 12, '5_11', "
            "if(${idade_respondente} < 18, '12_17', if(${idade_respondente} < 60, '18_59', '60_mais'))))",
        },
        {
            "type": "integer", "name": "pessoas_familia", "required": "yes",
            L_PT: "Quantas pessoas da sua família estão no abrigo, contando com você?",
            L_ES: "¿Cuántas personas de su familia están en el albergue, contándose usted?",
            "constraint": ". >= 1 and . <= 30",
            M_PT: "Informe um número entre 1 e 30.", M_ES: "Indique un número entre 1 y 30.",
        },
        {
            "type": "select_multiple necessidades", "name": "necessidades_prioritarias", "required": "yes",
            L_PT: "Quais são as necessidades mais urgentes da família?",
            L_ES: "¿Cuáles son las necesidades más urgentes de la familia?",
            H_PT: "Marque todas as que se aplicam.", H_ES: "Marque todas las que correspondan.",
            "constraint": "not(selected(., 'nenhuma') and count-selected(.) > 1)",
            M_PT: "'Nenhuma' não pode ser marcada junto com outras opções.",
            M_ES: "'Ninguna' no puede marcarse junto con otras opciones.",
        },
        {
            "type": "select_one sim_nao_recusa", "name": "inseguranca_violencia", "required": "yes",
            L_PT: "Desde que chegou ao abrigo, você ou alguém da família sofreu alguma violência ou se sentiu inseguro?",
            L_ES: "Desde que llegó al albergue, ¿usted o alguien de la familia sufrió alguna violencia o se sintió inseguro?",
        },
        {
            "type": "select_one sim_nao", "name": "aceita_contato", "required": "yes",
            L_PT: "Você aceita que a equipe entre em contato por telefone para dar retorno sobre os encaminhamentos?",
            L_ES: "¿Acepta que el equipo le contacte por teléfono para dar seguimiento a las derivaciones?",
            "dado_pessoal": "nao",
        },
        {
            "type": "text", "name": "telefone_contato", "relevant": "${aceita_contato} = 'sim'",
            L_PT: "Qual telefone podemos usar?", L_ES: "¿Qué teléfono podemos usar?",
            "constraint": "regex(., '^[0-9]{10,11}$')",
            M_PT: "Use só números, com DDD (10 ou 11 dígitos).", M_ES: "Use solo números, con código de área (10 u 11 dígitos).",
            "dado_pessoal": "sim",
            "justificativa_dados_pessoais": "Retorno sobre encaminhamentos solicitados pela família. Base legal: consentimento (LGPD art. 7º, I). Excluir após 90 dias.",
        },
        {"type": "end_group", "name": "entrevista"},
    ]

    choices_headers = ["list_name", "name", L_PT, L_ES]

    def opts(list_name, items):
        return [{"list_name": list_name, "name": n, L_PT: pt, L_ES: es} for n, pt, es in items]

    choices = (
        opts("sim_nao", [("sim", "Sim", "Sí"), ("nao", "Não", "No")])
        + opts("sim_nao_recusa", [
            ("sim", "Sim", "Sí"), ("nao", "Não", "No"),
            ("prefiro_nao_responder", "Prefiro não responder", "Prefiero no responder"),
        ])
        + opts("abrigos", [
            ("abrigo_a", "Abrigo Ipê Amarelo (fictício)", "Albergue Ipê Amarelo (ficticio)"),
            ("abrigo_b", "Abrigo Jatobá (fictício)", "Albergue Jatobá (ficticio)"),
        ])
        + opts("sexo", [
            ("feminino", "Feminino", "Femenino"), ("masculino", "Masculino", "Masculino"),
            ("prefiro_nao_responder", "Prefiro não responder", "Prefiero no responder"),
        ])
        + opts("necessidades", [
            ("alimentacao", "Alimentação", "Alimentación"),
            ("agua_potavel", "Água potável", "Agua potable"),
            ("kit_higiene", "Kit de higiene", "Kit de higiene"),
            ("colchao_roupa_de_cama", "Colchão e roupa de cama", "Colchón y ropa de cama"),
            ("atendimento_de_saude", "Atendimento de saúde", "Atención de salud"),
            ("documentacao", "Documentação", "Documentación"),
            ("nenhuma", "Nenhuma", "Ninguna"),
        ])
    )

    settings_headers = ["form_title", "form_id", "version", "default_language"]
    settings = [{
        "form_title": "Avaliação de necessidades em abrigo (exemplo fictício)",
        "form_id": "avaliacao_abrigo", "version": "2026110201", "default_language": PT,
    }]
    return {
        "survey": (survey_headers, survey),
        "choices": (choices_headers, choices),
        "settings": (settings_headers, settings),
    }


# ====================================================================== RUIM
# Reúne erros comuns em formulários montados sem seguir o padrão.

def bad_form() -> dict:
    survey_headers = ["type", "name", L_PT, L_ES, "relevant", "constraint"]
    survey = [
        {"type": "today", "name": "today"},
        {"type": "text", "name": "NomeCompleto", L_PT: "Nome completo do chefe da família"},
        {"type": "text", "name": "cpf", L_PT: "CPF", L_ES: "CPF"},
        {"type": "text", "name": "endereco_anterior", L_PT: "Endereço onde morava antes", L_ES: "Dirección anterior"},
        {"type": "select_one abrigos", "name": "abrigo", L_PT: "Abrigo", L_ES: "Albergue"},
        {"type": "date", "name": "data_chegada", L_PT: "Data de chegada", L_ES: "Fecha de llegada"},
        {"type": "select_one sexo", "name": "sexo", L_PT: "Sexo", L_ES: "Sexo"},
        {"type": "integer", "name": "idade", L_PT: "Idade", L_ES: "Edad", "constraint": ". >= 0"},
        {"type": "integer", "name": "pessoas_família", L_PT: "Pessoas na família"},
        {
            "type": "select_multiple tipos_violencia", "name": "violencias_sofridas",
            L_PT: "Você já foi vítima ou sofreu violências nesta vida? Se sim, quais?",
        },
        {
            "type": "select_one sim_nao", "name": "recebe_auxilio", L_PT: "Recebe algum auxílio?",
            "relevant": "${renda_familar} > 0",
        },
        {
            "type": "integer", "name": "quantidade_pessoas_com_necessidades_especificas",
            L_PT: "Quantas pessoas têm necessidades específicas?", L_ES: "¿Cuántas personas tienen necesidades específicas?",
            "constraint": ". >= 0 and . <= 20",
        },
        {"type": "text", "name": "abrigo", L_PT: "Nome do abrigo, se não estiver na lista"},
        {"type": "text", "name": "observacoes"},
    ]
    choices_headers = ["list_name", "name", L_PT, L_ES]

    def opt(list_name, name, pt, es=None):
        return {"list_name": list_name, "name": name, L_PT: pt, L_ES: es}

    choices = [
        opt("abrigos", "abrigo_a", "Abrigo Ipê Amarelo (fictício)", "Albergue Ipê Amarelo (ficticio)"),
        opt("abrigos", "abrigo_a", "Abrigo Jatobá (fictício)", "Albergue Jatobá (ficticio)"),
        opt("sexo", "m", "M", "M"),
        opt("sexo", "f", "F", "F"),
        # A pergunta do exemplo discutido na revisão do plano:
        opt("tipos_violencia", "nao_sofri", "Não sofri", "No sufrí"),
        opt("tipos_violencia", "violencia_baseada_em_genero", "Violência baseada em gênero", "Violencia basada en género"),
        opt("tipos_violencia", "crime de odio", "Crime de ódio", "Crimen de odio"),
        opt("tipos_violencia", "racismo_estrutural", "Racismo estrutural"),
        opt("tipos_violencia", "xenofobia_e_homofobia", "Xenofobia e homofobia", "Xenofobia y homofobia"),
        opt("escolaridade", "fundamental", "Ensino fundamental", "Educación primaria"),
        opt("escolaridade", "medio", "Ensino médio", "Educación secundaria"),
    ]
    settings_headers = ["form_title", "form_id"]
    settings = [{"form_title": "Cadastro abrigo", "form_id": "cadastro_abrigo"}]
    return {
        "survey": (survey_headers, survey),
        "choices": (choices_headers, choices),
        "settings": (settings_headers, settings),
    }


def main() -> None:
    good = ROOT / "examples" / "abrigo_bom.xlsx"
    save(good, good_form())
    save(ROOT / "examples" / "abrigo_ruim.xlsx", bad_form())
    # A pasta forms/ é monitorada pela GitHub Action: só o formulário aprovado fica lá.
    target = ROOT / "forms" / "avaliacao_abrigo.xlsx"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(good, target)
    print(f"copiado: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
