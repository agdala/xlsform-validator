"""Validação técnica oficial com pyxform e, opcionalmente, ODK Validate (TEC)."""

from __future__ import annotations

import io
import re
import shutil
from pathlib import Path

from ..engine import Finding, rule
from ..form import Form, form_to_xlsx

ROW_PATTERN = re.compile(r"\[row\s*:\s*(\d+)\]", re.IGNORECASE)
SHEET_PATTERN = re.compile(r"\b(survey|choices|settings)\b", re.IGNORECASE)


def _source(form: Form):
    path = Path(form.path)
    if path.suffix.lower() in (".xlsx", ".xls") and path.exists():
        return str(path)
    buffer = io.BytesIO()
    form_to_xlsx(form, buffer)
    return buffer.getvalue()


QUOTED = re.compile(r"'([^']+)'")


def _finding(text: str, form: Form) -> Finding:
    text = " ".join(str(text).split())
    row_match = ROW_PATTERN.search(text)
    sheet_match = SHEET_PATTERN.search(text)
    sheet = sheet_match.group(1).lower() if sheet_match else None
    row = int(row_match.group(1)) if row_match else None
    if row is None:
        # Algumas mensagens não trazem a linha, mas citam o valor entre aspas
        # (ex.: "Unknown question type 'inteiro'"). Localiza esse valor na survey.
        for value in QUOTED.findall(text):
            hit = next((r for r in form.survey if value in (r.get("type"), r.name)), None)
            if hit:
                sheet, row = "survey", hit.number
                break
    return Finding(message=f"pyxform: {text}", sheet=sheet, row=row)


def _convert(form: Form, validate: bool = False) -> tuple[str | None, list[str]]:
    """Retorna (erro, avisos). Guarda o resultado para não converter duas vezes."""
    cache = form.__dict__.setdefault("_pyxform_cache", {})
    if validate in cache:
        return cache[validate]
    from pyxform.errors import PyXFormError
    from pyxform.xls2xform import convert

    warnings: list[str] = []
    try:
        source = _source(form)
        file_type = ".xlsx" if isinstance(source, bytes) else None
        convert(xlsform=source, warnings=warnings, validate=validate, file_type=file_type)
        result = (None, warnings)
    except PyXFormError as exc:
        result = (str(exc), warnings)
    except Exception as exc:  # erros do ODK Validate e falhas inesperadas
        result = (f"{type(exc).__name__}: {exc}", warnings)
    cache[validate] = result
    return result


@rule("TEC-01")
def pyxform_converts(form: Form, params: dict) -> list[Finding]:
    error, _ = _convert(form)
    return [_finding(error, form)] if error else []


@rule("TEC-02")
def pyxform_warnings(form: Form, params: dict) -> list[Finding]:
    _, warnings = _convert(form)
    return [_finding(w, form) for w in warnings]


@rule("TEC-03")
def odk_validate(form: Form, params: dict) -> list[Finding]:
    if _convert(form)[0]:
        return []  # a TEC-01 já reportou que o formulário não converte
    if not shutil.which("java"):
        return [Finding("ODK Validate não pôde rodar: Java não está instalado.", suggestion="Instale Java 8+ ou desative a regra TEC-03.")]
    error, _ = _convert(form, validate=True)
    if not error:
        return []
    finding = _finding(error, form)
    finding.message = finding.message.replace("pyxform:", "ODK Validate:", 1)
    return [finding]
