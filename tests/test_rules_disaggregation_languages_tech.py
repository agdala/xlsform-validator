import shutil

import pytest
from conftest import base_dict, make_form

PT, ES = "label::Português (pt)", "label::Español (es)"


# ------------------------------------------------------------------ DES

def test_des01_missing_sex_question(check):
    data = base_dict()
    data["survey"][6]["name"] = "genero_x"
    assert check("DES-01", make_form(data))


def test_des01_non_standard_codes(check):
    data = base_dict()
    data["choices"] = [c for c in data["choices"] if c["list_name"] != "sexo"] + [
        {"list_name": "sexo", "name": "m", "label": "M"},
        {"list_name": "sexo", "name": "f", "label": "F"},
    ]
    [finding] = check("DES-01", make_form(data))
    assert "feminino" in finding.message


def test_des02_missing_age_group(check):
    data = base_dict()
    del data["survey"][8]  # remove o calculate faixa_etaria
    assert check("DES-02", make_form(data))


def test_des02_select_with_standard_list(check):
    data = base_dict()
    data["survey"][8] = {"type": "select_one faixas", "name": "faixa_etaria", "label": "Faixa"}
    data["choices"] += [
        {"list_name": "faixas", "name": c, "label": c} for c in ["0_4", "5_11", "12_17", "18_59", "60_mais"]
    ]
    assert not check("DES-02", make_form(data))
    data["choices"] = [c for c in data["choices"] if c["name"] != "60_mais"]
    [finding] = check("DES-02", make_form(data))
    assert "60_mais" in finding.message


# ------------------------------------------------------------------ IDI

def bilingual(data):
    for sheet in ("survey", "choices"):
        for row in data[sheet]:
            if "label" in row:
                text = row.pop("label")
                row[PT], row[ES] = text, f"{text} (es)"
    data["settings"][0]["default_language"] = "Português (pt)"
    return data


def test_idi_bilingual_form_passes(check):
    form = make_form(bilingual(base_dict()))
    assert not check("IDI-01", form)
    assert not check("IDI-02", form)
    assert not check("IDI-03", form)


def test_idi01_missing_translation(check):
    data = bilingual(base_dict())
    data["survey"][3][ES] = ""
    data["choices"][0][ES] = ""
    findings = check("IDI-01", make_form(data))
    assert {f.sheet for f in findings} == {"survey", "choices"}


def test_idi01_single_language_is_ignored(check):
    assert not check("IDI-01", make_form())


def test_idi02_hint_missing_translation(check):
    data = bilingual(base_dict())
    data["survey"][7]["hint::Português (pt)"] = "Em anos completos"
    assert check("IDI-02", make_form(data))


def test_idi03_default_language(check):
    data = bilingual(base_dict())
    del data["settings"][0]["default_language"]
    assert check("IDI-03", make_form(data))


# ------------------------------------------------------------------ TEC

def test_tec01_valid_form_converts(check):
    assert not check("TEC-01", make_form())


def test_tec01_reports_pyxform_error_with_row(check):
    data = base_dict()
    data["survey"][7]["type"] = "inteiro"  # tipo inexistente
    [finding] = check("TEC-01", make_form(data))
    assert finding.message.startswith("pyxform:")
    assert finding.row is not None


def test_tec02_returns_pyxform_warnings(check):
    data = base_dict()
    data["survey"][5]["label"] = ""  # grupo sem label gera aviso no pyxform
    findings = check("TEC-02", make_form(data))
    assert all(f.message.startswith("pyxform:") for f in findings)


@pytest.mark.skipif(not shutil.which("java"), reason="ODK Validate requer Java")
def test_tec03_odk_validate(configs):
    from xlsform_validator.engine import run_rules

    cfg = next(c for c in configs if c.id == "TEC-03")
    cfg_enabled = cfg.enabled
    cfg.enabled = True
    try:
        [result] = run_rules(make_form(), configs, only={"TEC-03"})
        assert result.findings == []
    finally:
        cfg.enabled = cfg_enabled
