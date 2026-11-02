import pytest
from conftest import base_dict, insert_in_group, make_form


def with_age_constraint(constraint):
    data = base_dict()
    data["survey"][7]["constraint"] = constraint
    return make_form(data)


# ------------------------------------------------------------------ VAL

@pytest.mark.parametrize(
    "constraint,fails",
    [
        (". >= 0 and . <= 120", False),
        (". >= 18 and . < 100", False),
        ("", True),
        (". >= 0", True),
        (". >= 0 and . <= 150", True),
        (". >= -1 and . <= 100", True),
    ],
)
def test_val01_age_limits(check, constraint, fails):
    assert bool(check("VAL-01", with_age_constraint(constraint))) is fails


def test_val02_date_without_future_check(check):
    data = base_dict()
    data["survey"][9]["constraint"] = ""
    assert check("VAL-02", make_form(data))


def test_val02_exception_for_scheduled_dates(check):
    data = insert_in_group(base_dict(), {"type": "date", "name": "data_retorno_previsto", "label": "Retorno"})
    assert not check("VAL-02", make_form(data))


def test_val03_number_without_limits(check):
    data = insert_in_group(base_dict(), {"type": "integer", "name": "pessoas", "label": "Pessoas"})
    assert check("VAL-03", make_form(data))


def test_val03_ignores_age_fields(check):
    assert not check("VAL-03", with_age_constraint(""))


# ------------------------------------------------------------------ MET

def test_met01_missing_metadata(check):
    data = base_dict()
    data["survey"] = data["survey"][2:]  # remove start e end
    findings = check("MET-01", make_form(data))
    assert {"start", "end"} == {f.message.split("'")[1] for f in findings}


# ------------------------------------------------------------------ CON

def test_con01_missing_consent(check):
    data = base_dict()
    data["survey"][3]["name"] = "aceita"
    assert check("CON-01", make_form(data))


def test_con02_consent_too_late(check):
    data = base_dict()
    early = [{"type": "text", "name": f"p{i}", "label": "x"} for i in range(3)]
    data["survey"][3:3] = early
    [finding] = check("CON-02", make_form(data))
    assert "nº 4" in finding.message


def test_con02_notes_and_metadata_do_not_count(check):
    data = base_dict()
    data["survey"][3:3] = [{"type": "note", "name": f"n{i}", "label": "x"} for i in range(5)]
    assert not check("CON-02", make_form(data))


def test_con03_question_outside_consent_group(check):
    data = base_dict()
    data["survey"].append({"type": "text", "name": "solta", "label": "Fora do grupo"})
    [finding] = check("CON-03", make_form(data))
    assert "solta" in finding.message


def test_con03_question_with_own_relevant(check):
    data = base_dict()
    data["survey"].append(
        {"type": "text", "name": "solta", "label": "x", "relevant": "${consentimento} = 'sim'"}
    )
    assert not check("CON-03", make_form(data))


# ------------------------------------------------------------------ LGPD

def test_lgpd01_detects_by_name_label_and_type(check):
    data = base_dict()
    for row in [
        {"type": "text", "name": "cpf_responsavel", "label": "Documento"},
        {"type": "text", "name": "contato", "label": "Qual o seu telefone?"},
        {"type": "phonenumber", "name": "phonenumber"},
    ]:
        insert_in_group(data, row)
    assert len(check("LGPD-01", make_form(data))) == 3


def test_lgpd01_false_positive_can_be_dismissed(check):
    data = insert_in_group(
        base_dict(), {"type": "text", "name": "nome_abrigo", "label": "Nome do abrigo", "dado_pessoal": "nao"}
    )
    assert not check("LGPD-01", make_form(data))
    assert not check("LGPD-02", make_form(data))


def test_lgpd01_confirmed_field_is_not_warned_again(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "telefone", "label": "Tel", "dado_pessoal": "sim"})
    assert not check("LGPD-01", make_form(data))


def test_lgpd02_requires_justification(check):
    row = {"type": "text", "name": "telefone", "label": "Telefone"}
    data = insert_in_group(base_dict(), row)
    assert check("LGPD-02", make_form(data))
    row["justificativa_dados_pessoais"] = "ok"  # curta demais
    assert check("LGPD-02", make_form(data))
    row["justificativa_dados_pessoais"] = "Retorno de encaminhamentos; base legal: consentimento."
    assert not check("LGPD-02", make_form(data))


def test_lgpd03_sensitive_question_without_opt_out(check):
    data = insert_in_group(base_dict(), {"type": "select_one sim_nao", "name": "sofreu_violencia", "label": "Sofreu?"})
    assert check("LGPD-03", make_form(data))
    data["choices"].append({"list_name": "sim_nao", "name": "prefiro_nao_responder", "label": "Prefiro não responder"})
    assert not check("LGPD-03", make_form(data))


def test_lgpd03_detects_topic_in_label(check):
    data = insert_in_group(
        base_dict(), {"type": "select_one sim_nao", "name": "p1", "label": "Você tem alguma deficiência?"}
    )
    assert check("LGPD-03", make_form(data))
