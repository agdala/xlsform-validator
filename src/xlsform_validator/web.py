"""Ponto de entrada da versão web (roda no navegador via Pyodide).

O navegador grava o arquivo do usuário no sistema de arquivos em memória do
Pyodide e chama ``validate_for_web``. Tudo é processado no próprio computador
do usuário; nada é enviado a servidores.
"""

from __future__ import annotations

import json
from pathlib import Path

from .annotate import annotate, is_annotated, ready_to_publish
from .engine import load_config
from .report import _file_json, to_markdown, validate_file

_CONFIGS: dict[str, list] = {}


def _configs(rules_path: str):
    if rules_path not in _CONFIGS:
        _CONFIGS[rules_path] = load_config(rules_path)
    return _CONFIGS[rules_path]


def validate_for_web(
    path: str, filename: str, rules_path: str, annotated_path: str, ready_path: str | None = None
) -> str:
    """Valida ``path``, grava a planilha anotada em ``annotated_path`` e, quando não
    há erros, o formulário pronto para publicar em ``ready_path``.

    Retorna um JSON com o relatório (``report``), o Markdown (``markdown``), se a
    planilha anotada (``annotated``) e o formulário pronto (``ready``) foram gerados,
    se marcas de uma anotação anterior foram removidas (``ready_cleaned``) e um
    aviso opcional (``note``).
    """
    report = validate_file(path, _configs(rules_path))
    report.path = filename
    if report.read_error:
        # A mensagem técnica cita o caminho interno do navegador; troca por uma orientação prática.
        report.read_error = (
            "O arquivo não parece ser uma planilha .xlsx válida. No KoboToolbox, use 'Download XLS'; "
            "se o arquivo for .xls (formato antigo), abra no Excel e salve como .xlsx."
        )
    annotated = ready = cleaned = False
    note = None
    if not report.read_error:
        data = Path(path).read_bytes()
        try:
            Path(annotated_path).write_bytes(annotate(data, report))
            annotated = True
        except Exception as exc:  # a anotação nunca deve impedir o relatório
            note = f"Não foi possível gerar a planilha anotada: {exc}"
        if ready_path and report.errors == 0:
            try:
                cleaned = is_annotated(data)
                Path(ready_path).write_bytes(ready_to_publish(data))
                ready = True
            except Exception as exc:
                note = f"Não foi possível gerar o formulário pronto para publicar: {exc}"
    return json.dumps(
        {
            "report": _file_json(report),
            "markdown": to_markdown([report]),
            "annotated": annotated,
            "ready": ready,
            "ready_cleaned": cleaned,
            "note": note,
        },
        ensure_ascii=False,
    )
