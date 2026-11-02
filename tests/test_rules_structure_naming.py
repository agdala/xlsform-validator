from conftest import base_dict, insert_in_group, make_form

from xlsform_validator.engine import REGISTRY, load_config


def test_base_form_passes_every_rule(configs):
    from xlsform_validator.engine import run_rules

    findings = [f for r in run_rules(make_form(), configs) for f in r.findings]
    assert findings == [], findings


def test_every_yaml_rule_has_an_implementation_and_vice_versa():
    ids = {c.id for c in load_config()}
    assert ids == set(REGISTRY)


# ------------------------------------------------------------------ EST

def test_est01_missing_survey(check):
    data = base_dict()
    del data["survey"]
    assert check("EST-01", make_form(data))


def test_est01_missing_choices_only_when_needed(check):
    data = base_dict()
    del data["choices"]
    assert check("EST-01", make_form(data))
    data["survey"] = [r for r in data["survey"] if not r["type"].startswith("select")]
    assert not check("EST-01", make_form(data))


def test_est01_misnamed_sheet_is_explained(check):
    form = make_form()
    del form.sheets["choices"]
    form.misnamed_sheets["choices"] = "Choices"
    [finding] = check("EST-01", form)
    assert "'Choices'" in finding.message


def test_est02_missing_settings(check):
    data = base_dict()
    del data["settings"]
    assert check("EST-02", make_form(data))
    assert not check("EST-02", make_form())


def test_est03_missing_columns(check):
    data = base_dict()
    for row in data["survey"]:
        row.pop("label", None)
    [finding] = check("EST-03", make_form(data))
    assert "label" in finding.message


def test_est03_accepts_translated_label(check):
    data = base_dict()
    for row in data["survey"]:
        if "label" in row:
            row["label::Português (pt)"] = row.pop("label")
    assert not check("EST-03", make_form(data))


def test_est04_accepts_list_name_with_space(check):
    data = base_dict()
    for row in data["choices"]:
        row["list name"] = row.pop("list_name")
    assert not check("EST-04", make_form(data))
    for row in data["choices"]:
        del row["list name"]
    assert check("EST-04", make_form(data))


def test_est05_form_id_and_version(check):
    data = base_dict()
    data["settings"] = [{"form_title": "Teste"}]
    findings = check("EST-05", make_form(data))
    assert {"form_id", "version"} == {f.message.split("'")[1] for f in findings}


def test_est06_version_format(check):
    data = base_dict()
    data["settings"][0]["version"] = "v2"
    assert check("EST-06", make_form(data))
    assert not check("EST-06", make_form())


def test_est07_question_without_label(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "obs"})
    [finding] = check("EST-07", make_form(data))
    assert "obs" in finding.message


# ------------------------------------------------------------------ NOM

def test_nom01_duplicate_names(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "idade", "label": "De novo"})
    [finding] = check("NOM-01", make_form(data))
    assert "idade" in finding.message


def test_nom01_ignores_end_group_name(check):
    assert not check("NOM-01", make_form())


def test_nom02_snake_case(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "NomeChefe", "label": "x"})
    [finding] = check("NOM-02", make_form(data))
    assert finding.suggestion == "Sugestão: nome_chefe"


def test_nom02_does_not_double_report_accents(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "situação", "label": "x"})
    assert not check("NOM-02", make_form(data))


def test_nom03_accents(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "situação", "label": "x"})
    [finding] = check("NOM-03", make_form(data))
    assert "situacao" in finding.suggestion


def test_nom04_max_length(check):
    data = insert_in_group(base_dict(), {"type": "text", "name": "a" * 33, "label": "x"})
    assert check("NOM-04", make_form(data))
    data = insert_in_group(base_dict(), {"type": "text", "name": "a" * 32, "label": "x"})
    assert not check("NOM-04", make_form(data))
