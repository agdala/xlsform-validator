from conftest import base_dict, insert_in_group, make_form


def add_multiple(data, codes, constraint=""):
    insert_in_group(
        data,
        {"type": "select_multiple nec", "name": "necessidades", "label": "Necessidades", "constraint": constraint},
    )
    data["choices"] += [{"list_name": "nec", "name": c, "label": c.title()} for c in codes]
    return data


# ------------------------------------------------------------------ OPC

def test_opc01_missing_list(check):
    data = insert_in_group(base_dict(), {"type": "select_one cores", "name": "cor", "label": "Cor"})
    [finding] = check("OPC-01", make_form(data))
    assert "cores" in finding.message


def test_opc01_accepts_or_other_and_spaced_type(check):
    data = insert_in_group(base_dict(), {"type": "select one sim_nao or_other", "name": "x", "label": "x"})
    assert not check("OPC-01", make_form(data))


def test_opc02_duplicate_choice(check):
    data = base_dict()
    data["choices"].append({"list_name": "sim_nao", "name": "sim", "label": "Sim de novo"})
    assert check("OPC-02", make_form(data))
    data["settings"][0]["allow_choice_duplicates"] = "yes"
    assert not check("OPC-02", make_form(data))


def test_opc03_orphan_list(check):
    data = base_dict()
    data["choices"].append({"list_name": "orfa", "name": "a", "label": "A"})
    [finding] = check("OPC-03", make_form(data))
    assert "orfa" in finding.message


def test_opc04_space_in_multiple_code_with_suggestion(check):
    data = add_multiple(base_dict(), ["crime de ódio", "racismo_estrutural"])
    [finding] = check("OPC-04", make_form(data))
    assert finding.suggestion.endswith("crime_de_odio")


def test_opc04_long_labels_are_fine(check):
    data = add_multiple(base_dict(), ["violencia_baseada_em_genero"])
    data["choices"][-1]["label"] = "Violência baseada em gênero com várias palavras"
    assert not check("OPC-04", make_form(data))


def test_opc04_ignores_select_one(check):
    data = base_dict()
    data["choices"].append({"list_name": "sim_nao", "name": "talvez sim", "label": "Talvez"})
    assert not check("OPC-04", make_form(data))


def test_opc05_exclusive_option_without_constraint(check):
    data = add_multiple(base_dict(), ["nenhuma", "alimentacao"])
    [finding] = check("OPC-05", make_form(data))
    assert "nenhuma" in finding.suggestion


def test_opc05_exclusive_option_with_constraint(check):
    data = add_multiple(
        base_dict(), ["nenhuma", "alimentacao"],
        constraint="not(selected(., 'nenhuma') and count-selected(.) > 1)",
    )
    data["survey"][-2]["constraint_message"] = "x"
    assert not check("OPC-05", make_form(data))


# ------------------------------------------------------------------ LOG

def test_log01_unknown_reference_with_suggestion(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "x", "label": "x", "relevant": "${idadee} > 18"})
    [finding] = check("LOG-01", make_form(data))
    assert "idadee" in finding.message
    assert "${idade}" in finding.suggestion


def test_log01_checks_calculation_and_settings(check):
    data = base_dict()
    data["survey"][8]["calculation"] = "${nao_existe} + 1"
    data["settings"][0]["instance_name"] = "concat(${fantasma}, '-')"
    assert len(check("LOG-01", make_form(data))) == 2


def test_log02_constraint_without_message(check):
    data = base_dict()
    del data["survey"][7]["constraint_message"]
    assert check("LOG-02", make_form(data))


def test_log02_translated_message_counts(check):
    data = base_dict()
    data["survey"][7]["constraint_message::Español (es)"] = data["survey"][7].pop("constraint_message")
    assert not check("LOG-02", make_form(data))
