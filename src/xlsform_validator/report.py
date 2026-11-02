"""Execução por arquivo e geração dos relatórios em Markdown e JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from . import rules as _rules  # noqa: F401  (registra as regras)
from .engine import Finding, RuleConfig, RuleResult, run_rules
from .form import Form, FormReadError

STATUS_OK = "aprovado"
STATUS_WARN = "aprovado_com_avisos"
STATUS_FAIL = "reprovado"
STATUS_UNREADABLE = "ilegivel"

STATUS_TEXT = {
    STATUS_OK: "✅ Aprovado",
    STATUS_WARN: "⚠️ Aprovado com avisos",
    STATUS_FAIL: "❌ Reprovado",
    STATUS_UNREADABLE: "⛔ Arquivo ilegível",
}


@dataclass
class FileReport:
    path: str
    results: list[RuleResult] = field(default_factory=list)
    read_error: str | None = None

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.results for f in r.findings]

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "erro")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "aviso")

    @property
    def status(self) -> str:
        if self.read_error:
            return STATUS_UNREADABLE
        if self.errors:
            return STATUS_FAIL
        return STATUS_WARN if self.warnings else STATUS_OK

    @property
    def exit_code(self) -> int:
        return {STATUS_UNREADABLE: 2, STATUS_FAIL: 1}.get(self.status, 0)


def validate_file(path: str | Path, configs: list[RuleConfig]) -> FileReport:
    try:
        form = Form.from_xlsx(path)
    except FormReadError as exc:
        return FileReport(path=str(path), read_error=str(exc))
    return FileReport(path=str(path), results=run_rules(form, configs))


def validate_form(form: Form, configs: list[RuleConfig]) -> FileReport:
    return FileReport(path=form.path, results=run_rules(form, configs))


# ------------------------------------------------------------------ JSON

def to_json(reports: list[FileReport]) -> str:
    payload = {
        "tool": "xlsform-validator",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [_file_json(r) for r in reports],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _file_json(report: FileReport) -> dict:
    return {
        "file": report.path,
        "status": report.status,
        "read_error": report.read_error,
        "summary": {
            "errors": report.errors,
            "warnings": report.warnings,
            "rules_checked": len(report.results),
            "rules_failed": sum(1 for r in report.results if r.findings),
        },
        "rules": [
            {
                "rule_id": r.config.id,
                "group": r.config.group,
                "severity": r.config.severity,
                "description": r.config.description,
                "why_it_matters": r.config.why,
                "passed": not r.findings,
                "findings": [
                    {k: v for k, v in f.to_dict().items() if k not in ("rule_id", "group", "severity")}
                    for f in r.findings
                ],
            }
            for r in report.results
        ],
    }


# ------------------------------------------------------------------ Markdown

def _cell(value) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def to_markdown(reports: list[FileReport], title: str = "Relatório de validação XLSForm") -> str:
    lines = [f"# {title}", ""]
    if len(reports) > 1:
        lines += ["| Arquivo | Status | Erros | Avisos |", "|---|---|---:|---:|"]
        for r in reports:
            lines.append(f"| `{r.path}` | {STATUS_TEXT[r.status]} | {r.errors} | {r.warnings} |")
        lines.append("")
    for r in reports:
        lines += _file_markdown(r, heading="##" if len(reports) > 1 else None)
    lines.append(f"<sub>Gerado por xlsform-validator {__version__}.</sub>")
    return "\n".join(lines).rstrip() + "\n"


def _file_markdown(report: FileReport, heading: str | None) -> list[str]:
    lines: list[str] = []
    if heading:
        lines += [f"{heading} `{report.path}`", ""]
    else:
        lines += [f"**Arquivo:** `{report.path}`", ""]
    sub = "###" if heading else "##"

    if report.read_error:
        lines += [f"**Status:** {STATUS_TEXT[report.status]}", "", f"> {report.read_error}", ""]
        return lines

    failed = [r for r in report.results if r.findings]
    lines += [
        f"**Status:** {STATUS_TEXT[report.status]}",
        "",
        "| Erros | Avisos | Regras verificadas | Regras com problema |",
        "|---:|---:|---:|---:|",
        f"| {report.errors} | {report.warnings} | {len(report.results)} | {len(failed)} |",
        "",
    ]
    if not failed:
        lines += ["Nenhum problema encontrado. O formulário segue o padrão de qualidade.", ""]
        return lines

    lines += [f"{sub} Resumo por regra", "", "| Regra | Severidade | Ocorrências | Descrição |", "|---|---|---:|---|"]
    for r in sorted(failed, key=_order):
        icon = "❌" if r.config.severity == "erro" else "⚠️"
        lines.append(f"| {r.config.id} | {icon} {r.config.severity} | {len(r.findings)} | {_cell(r.config.description)} |")
    lines.append("")

    lines += [f"{sub} O que corrigir", ""]
    for r in sorted(failed, key=_order):
        icon = "❌" if r.config.severity == "erro" else "⚠️"
        lines += [
            f"**{icon} {r.config.id} · {r.config.description}**",
            "",
            f"*Por que importa:* {r.config.why}",
            "",
            "| Aba | Linha | Problema | Como corrigir |",
            "|---|---:|---|---|",
        ]
        for f in r.findings:
            lines.append(f"| {_cell(f.sheet)} | {_cell(f.row)} | {_cell(f.message)} | {_cell(f.suggestion)} |")
        lines.append("")
    return lines


def _order(result: RuleResult):
    return (0 if result.config.severity == "erro" else 1, result.config.id)


def write_reports(reports: list[FileReport], out_dir: Path, formats: list[str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    if "md" in formats:
        p = out_dir / "relatorio.md"
        p.write_text(to_markdown(reports), encoding="utf-8")
        written.append(p)
    if "json" in formats:
        p = out_dir / "relatorio.json"
        p.write_text(to_json(reports), encoding="utf-8")
        written.append(p)
    return written
