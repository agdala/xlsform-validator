"""Interface de linha de comando.

Exemplos:
    xlsform-validator formulario.xlsx
    xlsform-validator forms/*.xlsx --formato json
    xlsform-validator formulario.xlsx --saida relatorios/ --formato md json
    xlsform-validator formulario.xlsx --regras minhas_regras.yaml --odk-validate
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .engine import ConfigError, default_rules_path, load_config
from .report import to_json, to_markdown, validate_file, write_reports


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xlsform-validator",
        description="Valida formulários XLSForm (KoboToolbox/ODK) contra um padrão de qualidade e governança.",
    )
    p.add_argument("arquivos", nargs="*", type=Path, help="Um ou mais arquivos .xlsx")
    p.add_argument("--regras", type=Path, help="Arquivo YAML de regras (padrão: regras embutidas)")
    p.add_argument(
        "--formato", nargs="+", choices=["md", "json"], default=["md"],
        help="Formato(s) do relatório (padrão: md)",
    )
    p.add_argument("--saida", type=Path, help="Pasta onde gravar relatorio.md / relatorio.json (padrão: imprime na tela)")
    p.add_argument("--odk-validate", action="store_true", help="Também roda o ODK Validate (requer Java)")
    p.add_argument("--exportar-regras", type=Path, metavar="ARQUIVO", help="Copia o YAML de regras padrão para personalizar")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.exportar_regras:
        shutil.copyfile(default_rules_path(), args.exportar_regras)
        print(f"Regras padrão copiadas para {args.exportar_regras}")
        return 0
    if not args.arquivos:
        build_parser().error("informe pelo menos um arquivo .xlsx")

    try:
        configs = load_config(args.regras)
    except ConfigError as exc:
        print(f"Erro na configuração: {exc}", file=sys.stderr)
        return 2
    if args.odk_validate:
        for cfg in configs:
            if cfg.id == "TEC-03":
                cfg.enabled = True

    reports = [validate_file(path, configs) for path in args.arquivos]

    if args.saida:
        for written in write_reports(reports, args.saida, args.formato):
            print(f"Relatório gravado em {written}", file=sys.stderr)
    else:
        if "md" in args.formato:
            print(to_markdown(reports))
        if "json" in args.formato:
            print(to_json(reports))

    for r in reports:
        print(f"{r.path}: {r.status} (erros: {r.errors}, avisos: {r.warnings})", file=sys.stderr)
    return max(r.exit_code for r in reports)


if __name__ == "__main__":
    sys.exit(main())
