import json
from pathlib import Path

import pytest
from conftest import base_dict, make_form

from xlsform_validator.cli import main
from xlsform_validator.engine import ConfigError, load_config
from xlsform_validator.form import Form, form_to_xlsx

ROOT = Path(__file__).resolve().parents[1]
GOOD = ROOT / "examples" / "abrigo_bom.xlsx"
BAD = ROOT / "examples" / "abrigo_ruim.xlsx"


def test_good_example_exits_zero(capsys):
    assert main([str(GOOD)]) == 0
    assert "Aprovado" in capsys.readouterr().out


def test_bad_example_exits_one_and_lists_rules(capsys):
    assert main([str(BAD)]) == 1
    out = capsys.readouterr().out
    for rule_id in ["CON-01", "OPC-04", "LGPD-02", "NOM-01", "TEC-01"]:
        assert rule_id in out


def test_unreadable_file_exits_two(tmp_path):
    bogus = tmp_path / "x.xlsx"
    bogus.write_text("não é planilha")
    assert main([str(bogus)]) == 2
    assert main([str(tmp_path / "nao_existe.xlsx")]) == 2


def test_json_output_structure(tmp_path):
    assert main([str(BAD), "--formato", "md", "json", "--saida", str(tmp_path)]) == 1
    payload = json.loads((tmp_path / "relatorio.json").read_text(encoding="utf-8"))
    report = payload["files"][0]
    assert report["status"] == "reprovado"
    assert report["summary"]["errors"] > 0
    failed = [r for r in report["rules"] if not r["passed"]]
    assert all({"rule_id", "severity", "findings", "why_it_matters"} <= r.keys() for r in failed)
    assert all("row" in f and "sheet" in f for r in failed for f in r["findings"])
    assert (tmp_path / "relatorio.md").exists()


def test_warnings_only_exit_zero(tmp_path):
    data = base_dict()
    data["choices"].append({"list_name": "orfa", "name": "a", "label": "A"})  # OPC-03 é aviso
    path = form_to_xlsx(make_form(data), tmp_path / "avisos.xlsx")
    assert main([str(path)]) == 0


def test_xlsx_round_trip_keeps_row_numbers(tmp_path):
    path = form_to_xlsx(make_form(), tmp_path / "f.xlsx")
    form = Form.from_xlsx(path)
    assert form.survey[0].number == 2
    assert form.survey[3].name == "consentimento"


def test_custom_rules_file_can_disable_rule(tmp_path):
    rules = tmp_path / "regras.yaml"
    assert main(["--exportar-regras", str(rules)]) == 0
    text = rules.read_text(encoding="utf-8")
    rules.write_text(text.replace("severidade: erro", "severidade: aviso"), encoding="utf-8")
    # Com todas as regras rebaixadas para aviso, o formulário ruim não bloqueia.
    assert main([str(BAD), "--regras", str(rules)]) == 0


def test_invalid_severity_is_rejected(tmp_path):
    rules = tmp_path / "r.yaml"
    rules.write_text(
        "regras:\n  NOM-01:\n    grupo: x\n    descricao: x\n    severidade: grave\n    por_que_importa: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(rules)
