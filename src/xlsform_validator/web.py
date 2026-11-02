"""Ponto de entrada da versão web (roda no navegador via Pyodide).

O navegador grava o arquivo do usuário no sistema de arquivos em memória do
Pyodide e chama ``validate_for_web``. Tudo é processado no próprio computador
do usuário; nada é enviado a servidores.
"""

from __future__ import annotations

import json
from pathlib import Path

from .annotate import annotate
from .engine import load_config
from .report import _file_json, to_markdown, validate_file

_CONFIGS: dict[str, list] = {}


def _configs(rules_path: str):
    if rules_path not in _CONFIGS:
        _CONFIGS[rules_path] = load_config(rules_path)
    return _CONFIGS[rules_path]


def validate_for_web(path: str, filename: str, rules_path: str, annotated_path: str) -> str:
    """Valida ``path`` e grava a planilha anotada em ``annotated_path``.

    Retorna um JSON com o relatório (``report``), o Markdown (``markdown``),
    se a planilha anotada foi gerada (``annotated``) e um aviso opcional (``note``).
    """
    report = validate_file(path, _configs(rules_path))
    report.path = filename
    if report.read_error:
        # A mensagem técnica cita o caminho interno do navegador; troca por uma orientação prática.
        report.read_error = (
            "O arquivo não parece ser uma planilha .xlsx válida. No KoboToolbox, use 'Download XLS'; "
            "se o arquivo for .xls (formato antigo), abra no Excel e salve como .xlsx."
        )
    annotated, note = False, None
    if not report.read_error:
        try:
            Path(annotated_path).write_bytes(annotate(Path(path).read_bytes(), report))
            annotated = True
        except Exception as exc:  # a anotação nunca deve impedir o relatório
            note = f"Não foi possível gerar a planilha anotada: {exc}"
    return json.dumps(
        {
            "report": _file_json(report),
            "markdown": to_markdown([report]),
            "annotated": annotated,
            "note": note,
        },
        ensure_ascii=False,
    )
