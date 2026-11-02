"""Gera uma cópia da planilha com os problemas marcados nas próprias células.

Para quem não é técnico, "aba survey, linha 12" é abstrato. A planilha anotada
mostra o problema onde ele está: a linha fica colorida, a célula exata ganha um
comentário com o que corrigir e uma aba de resumo lista tudo com links.
"""

from __future__ import annotations

import io
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .form import normalize_header
from .report import STATUS_TEXT, FileReport

SUMMARY_SHEET = "validacao"
AUTHOR = "xlsform-validator"

FILL = {
    "erro": (PatternFill("solid", fgColor="FDE2E1"), PatternFill("solid", fgColor="F4A6A0")),
    "aviso": (PatternFill("solid", fgColor="FFF6D5"), PatternFill("solid", fgColor="FFDF80")),
}

# Coluna mais provável do problema, quando a regra não informa uma específica.
DEFAULT_COLUMN = {
    "EST-06": "version", "EST-07": "label",
    "NOM-01": "name", "NOM-02": "name", "NOM-03": "name", "NOM-04": "name",
    "OPC-01": "type", "OPC-02": "name", "OPC-03": "list_name", "OPC-04": "name", "OPC-05": "constraint",
    "LOG-02": "constraint",
    "VAL-01": "constraint", "VAL-02": "constraint", "VAL-03": "constraint",
    "CON-02": "name", "CON-03": "relevant",
    "LGPD-01": "name", "LGPD-02": "justificativa_dados_pessoais", "LGPD-03": "type",
    "DES-01": "type", "DES-02": "type",
    "IDI-03": "default_language",
}


def _header_map(ws) -> dict[str, int]:
    headers: dict[str, int] = {}
    for cell in ws[1]:
        if cell.value is not None and str(cell.value).strip():
            headers.setdefault(normalize_header(cell.value), cell.column)
    return headers


def _target_column(finding, headers: dict[str, int]) -> int:
    candidates = [finding.column, DEFAULT_COLUMN.get(finding.rule_id), "name", "type"]
    for col in candidates:
        if col and col in headers:
            return headers[col]
        if col == "label":  # formulário multilíngue: usa a primeira coluna label::idioma
            for h, idx in headers.items():
                if h.startswith("label::"):
                    return idx
    return 1


def annotate(source: str | Path | bytes, report: FileReport) -> bytes:
    """Devolve o .xlsx anotado (bytes). ``source`` é o arquivo original."""
    stream = io.BytesIO(source) if isinstance(source, bytes) else source
    wb = load_workbook(stream)
    if SUMMARY_SHEET in wb.sheetnames:  # arquivo já anotado antes: recomeça o resumo
        del wb[SUMMARY_SHEET]

    # Agrupa os problemas por célula, para um único comentário por célula.
    by_cell: dict[tuple[str, int, int], list] = defaultdict(list)
    by_row: dict[tuple[str, int], str] = {}
    locations: dict[int, str] = {}
    for f in report.findings:
        if not f.sheet or not f.row or f.sheet not in wb.sheetnames:
            continue
        ws = wb[f.sheet]
        col = _target_column(f, _header_map(ws))
        by_cell[(f.sheet, f.row, col)].append(f)
        current = by_row.get((f.sheet, f.row))
        by_row[(f.sheet, f.row)] = "erro" if "erro" in (current, f.severity) else "aviso"
        locations[id(f)] = f"{f.sheet}!{get_column_letter(col)}{f.row}"

    for (sheet, row), severity in by_row.items():
        ws = wb[sheet]
        light, _ = FILL[severity]
        for col in range(1, (ws.max_column or 1) + 1):
            ws.cell(row=row, column=col).fill = light

    for (sheet, row, col), findings in by_cell.items():
        cell = wb[sheet].cell(row=row, column=col)
        severity = "erro" if any(f.severity == "erro" for f in findings) else "aviso"
        cell.fill = FILL[severity][1]
        parts = []
        for f in findings:
            text = f"[{f.severity.upper()}] {f.rule_id}: {_plain(f.message)}"
            if f.suggestion:
                text += f"\nComo corrigir: {f.suggestion}"
            parts.append(text)
        comment = Comment("\n\n".join(parts), AUTHOR)
        comment.width = 420
        comment.height = min(110 + 70 * len(parts), 600)
        cell.comment = comment

    _summary_sheet(wb, report, locations)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _plain(message: str) -> str:
    return message.replace("pyxform: ", "Conversor oficial: ", 1)


def _summary_sheet(wb, report: FileReport, locations: dict[int, str]) -> None:
    ws = wb.create_sheet(SUMMARY_SHEET, 0)
    wb.active = 0
    for other in wb.worksheets[1:]:
        other.sheet_view.tabSelected = False

    ws["A1"] = "Resultado da validação"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = STATUS_TEXT[report.status]
    ws["A2"].font = Font(bold=True, size=12)
    ws["A3"] = f"Erros: {report.errors}    Avisos: {report.warnings}"
    ws["A4"] = (
        "Linhas com problema estão coloridas nas abas do formulário (vermelho = erro, amarelo = aviso). "
        "Passe o mouse sobre a célula mais escura para ver o comentário. "
        "Apague esta aba antes de publicar o formulário."
    )
    ws["A4"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A4:F4")
    ws.row_dimensions[4].height = 45

    headers = ["Severidade", "Regra", "Onde", "Problema", "Como corrigir", "Por que importa"]
    ws.append([])
    ws.append(headers)
    header_row = ws.max_row
    for cell in ws[header_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")

    ordered = sorted(
        ((r.config, f) for r in report.results for f in r.findings),
        key=lambda cf: (cf[0].severity != "erro", cf[0].id, cf[1].sheet or "", cf[1].row or 0),
    )
    for cfg, f in ordered:
        where = f"{f.sheet}, linha {f.row}" if f.sheet and f.row else (f.sheet or "formulário")
        ws.append([f.severity, cfg.id, where, _plain(f.message), f.suggestion or "", cfg.why])
        r = ws.max_row
        ws.cell(row=r, column=1).fill = FILL[f.severity][1]
        loc = locations.get(id(f))
        if loc:
            sheet, ref = loc.split("!")
            link = ws.cell(row=r, column=3)
            link.hyperlink = f"#'{sheet}'!{ref}"
            link.font = Font(color="0563C1", underline="single")
        for c in ws[r]:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    if not ordered:
        ws.append(["", "", "", "Nenhum problema encontrado. O formulário segue o padrão de qualidade."])

    for col, width in zip("ABCDEF", (11, 9, 18, 60, 45, 50)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    # Impressão: paisagem, todas as colunas em uma página de largura.
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
