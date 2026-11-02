import json
from pathlib import Path

from conftest import base_dict, insert_in_group, make_form
from openpyxl import load_workbook
from pyxform.xls2xform import convert

from xlsform_validator.annotate import SUMMARY_SHEET, annotate
from xlsform_validator.cli import main
from xlsform_validator.engine import load_config
from xlsform_validator.form import form_to_xlsx
from xlsform_validator.pyxform_messages import translate
from xlsform_validator.report import validate_file
from xlsform_validator.web import validate_for_web

ROOT = Path(__file__).resolve().parents[1]
BAD = ROOT / "examples" / "abrigo_ruim.xlsx"
GOOD = ROOT / "examples" / "abrigo_bom.xlsx"
RULES = ROOT / "src" / "xlsform_validator" / "rules.yaml"


def annotated_workbook(path, tmp_path):
    report = validate_file(path, load_config())
    out = tmp_path / "anotado.xlsx"
    out.write_bytes(annotate(Path(path).read_bytes(), report))
    return load_workbook(out), report


def test_annotation_marks_exact_cell_with_comment(tmp_path):
    data = insert_in_group(base_dict(), {"type": "text", "name": "NomeChefe", "label": "Chefe"})
    path = form_to_xlsx(make_form(data), tmp_path / "f.xlsx")
    wb, _ = annotated_workbook(path, tmp_path)
    ws = wb["survey"]
    name_col = [c.value for c in ws[1]].index("name") + 1
    row = next(r for r in range(2, ws.max_row + 1) if ws.cell(r, name_col).value == "NomeChefe")
    cell = ws.cell(row, name_col)
    assert cell.comment is not None
    assert "NOM-02" in cell.comment.text and "nome_chefe" in cell.comment.text
    assert cell.fill.fgColor.rgb.endswith("F4A6A0")  # erro: tom forte na célula


def test_annotation_summary_sheet_first_with_links(tmp_path):
    wb, report = annotated_workbook(BAD, tmp_path)
    assert wb.sheetnames[0] == SUMMARY_SHEET
    ws = wb[SUMMARY_SHEET]
    links = [c.hyperlink.location or c.hyperlink.target for row in ws.iter_rows() for c in row if c.hyperlink]
    assert links and all("!" in link for link in links)
    rows_with_rule = [r for r in ws.iter_rows(values_only=True) if r[1] and str(r[1])[:3].isalpha() and "-" in str(r[1])]
    assert len(rows_with_rule) == report.errors + report.warnings


def test_annotated_good_form_still_converts(tmp_path):
    report = validate_file(GOOD, load_config())
    out = tmp_path / "bom_anotado.xlsx"
    out.write_bytes(annotate(GOOD.read_bytes(), report))
    convert(xlsform=str(out))  # a aba extra não impede a publicação


def test_reannotating_replaces_summary(tmp_path):
    wb, _ = annotated_workbook(BAD, tmp_path)
    first = tmp_path / "anotado.xlsx"
    report = validate_file(first, load_config())
    second = load_workbook(__import__("io").BytesIO(annotate(first.read_bytes(), report)))
    assert second.sheetnames.count(SUMMARY_SHEET) == 1


def test_cli_anotar(tmp_path):
    assert main([str(BAD), "--anotar", "--saida", str(tmp_path)]) == 1
    assert (tmp_path / "abrigo_ruim_anotado.xlsx").exists()


def test_translate_known_and_unknown_messages():
    assert "repetido" in translate(
        "[row : 5] On the 'survey' sheet, the 'name' value 'idade' is invalid. "
        "Questions, groups, and repeats must be unique within their nearest parent group or repeat, or the survey if not inside a group or repeat."
    )
    assert "inteiro" in translate("Unknown question type 'inteiro'.")
    assert translate("Some brand new message") is None


def test_web_entry_point(tmp_path):
    out = tmp_path / "anotado.xlsx"
    result = json.loads(validate_for_web(str(BAD), "meu_form.xlsx", str(RULES), str(out)))
    assert result["report"]["file"] == "meu_form.xlsx"
    assert result["report"]["status"] == "reprovado"
    assert result["annotated"] is True and out.exists()
    assert "Reprovado" in result["markdown"]


def test_web_entry_point_unreadable_file(tmp_path):
    bogus = tmp_path / "x.xlsx"
    bogus.write_text("não é planilha")
    result = json.loads(validate_for_web(str(bogus), "x.xlsx", str(RULES), str(tmp_path / "a.xlsx")))
    assert result["report"]["status"] == "ilegivel"
    assert result["annotated"] is False
    assert str(tmp_path) not in result["report"]["read_error"]


def test_rules_json_matches_yaml(tmp_path):
    import yaml

    raw = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    assert [c.id for c in load_config(path)] == [c.id for c in load_config(RULES)]
