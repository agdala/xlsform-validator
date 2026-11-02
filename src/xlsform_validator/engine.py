"""Motor de validação: registro de regras, configuração YAML e execução."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Callable

import yaml

from .form import Form

SEVERITIES = ("erro", "aviso")


@dataclass
class Finding:
    """Um problema encontrado. ``sheet`` e ``row`` apontam o local na planilha."""

    message: str
    sheet: str | None = None
    row: int | None = None
    suggestion: str | None = None
    # Preenchidos pelo motor a partir da configuração:
    rule_id: str = ""
    group: str = ""
    severity: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuleConfig:
    id: str
    group: str
    description: str
    severity: str
    why: str
    enabled: bool = True
    params: dict = field(default_factory=dict)


@dataclass
class RuleResult:
    config: RuleConfig
    findings: list[Finding]


CheckFn = Callable[[Form, dict], list[Finding]]
REGISTRY: dict[str, CheckFn] = {}


def rule(rule_id: str) -> Callable[[CheckFn], CheckFn]:
    """Registra a função que implementa uma regra do arquivo YAML."""

    def decorator(fn: CheckFn) -> CheckFn:
        if rule_id in REGISTRY:
            raise ValueError(f"Regra registrada duas vezes: {rule_id}")
        REGISTRY[rule_id] = fn
        return fn

    return decorator


class ConfigError(Exception):
    pass


def default_rules_path() -> Path:
    return Path(str(resources.files("xlsform_validator") / "rules.yaml"))


def load_config(path: str | Path | None = None) -> list[RuleConfig]:
    from . import rules  # noqa: F401  (registra as implementações)

    path = Path(path) if path else default_rules_path()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Não foi possível ler o arquivo de regras '{path}': {exc}") from exc

    rules_raw = raw.get("regras")
    if not isinstance(rules_raw, dict):
        raise ConfigError("O arquivo de regras precisa de uma chave 'regras' com um mapa de regras.")

    configs: list[RuleConfig] = []
    for rule_id, item in rules_raw.items():
        item = item or {}
        missing = [k for k in ("grupo", "descricao", "severidade", "por_que_importa") if not item.get(k)]
        if missing:
            raise ConfigError(f"Regra {rule_id}: faltam os campos {', '.join(missing)}.")
        severity = str(item["severidade"]).strip().lower()
        if severity not in SEVERITIES:
            raise ConfigError(
                f"Regra {rule_id}: severidade '{item['severidade']}' inválida. Use 'erro' ou 'aviso'."
            )
        if rule_id not in REGISTRY:
            raise ConfigError(f"Regra {rule_id} está no YAML, mas não existe implementação para ela.")
        configs.append(
            RuleConfig(
                id=rule_id,
                group=str(item["grupo"]),
                description=str(item["descricao"]).strip(),
                severity=severity,
                why=str(item["por_que_importa"]).strip(),
                enabled=bool(item.get("ativa", True)),
                params=item.get("parametros") or {},
            )
        )
    return configs


def run_rules(form: Form, configs: list[RuleConfig], only: set[str] | None = None) -> list[RuleResult]:
    results: list[RuleResult] = []
    for cfg in configs:
        if not cfg.enabled or (only is not None and cfg.id not in only):
            continue
        findings = REGISTRY[cfg.id](form, cfg.params) or []
        for f in findings:
            f.rule_id, f.group, f.severity = cfg.id, cfg.group, cfg.severity
        results.append(RuleResult(config=cfg, findings=findings))
    return results
