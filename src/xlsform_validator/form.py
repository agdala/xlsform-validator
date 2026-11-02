"""Modelo em memória de um XLSForm e leitura do arquivo .xlsx.

O validador não depende do pyxform para ler a planilha: ele precisa preservar o
número real de cada linha do Excel para que o relatório aponte exatamente onde
corrigir, inclusive em formulários que o pyxform não consegue converter.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from openpyxl import load_workbook

SURVEY = "survey"
CHOICES = "choices"
SETTINGS = "settings"
KNOWN_SHEETS = (SURVEY, CHOICES, SETTINGS)

# Sinônimos de cabeçalho aceitos pela especificação / pyxform.
HEADER_ALIASES = {
    "list name": "list_name",
    "constraint message": "constraint_message",
    "required message": "required_message",
    "choice filter": "choice_filter",
    "repeat count": "repeat_count",
}

# Tipos de metadado: são preenchidos pelo aplicativo e não têm label.
METADATA_TYPES = {
    "start", "end", "today", "deviceid", "subscriberid", "simserial",
    "phonenumber", "username", "email", "audit", "start-geopoint",
    "background-audio",
}
GROUP_BEGIN = {"begin_group", "begin_repeat"}
GROUP_END = {"end_group", "end_repeat"}
SELECT_TYPES = {"select_one", "select_multiple", "rank"}

REF_PATTERN = re.compile(r"\$\{([^}]*)\}")


class FormReadError(Exception):
    """O arquivo não pôde ser lido como planilha XLSForm."""


def normalize_header(header: str) -> str:
    """Padroniza um cabeçalho: tira espaços, aplica sinônimos e põe a parte
    base em minúsculas (``Label::Español (es)`` vira ``label::Español (es)``)."""
    header = str(header).strip()
    if "::" in header:
        base, lang = header.split("::", 1)
        base = HEADER_ALIASES.get(base.strip().lower(), base.strip().lower())
        return f"{base}::{lang.strip()}"
    lowered = header.lower()
    return HEADER_ALIASES.get(lowered, lowered)


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def to_snake_case(text: str) -> str:
    """Gera um nome de variável sugerido, no mesmo padrão do Formbuilder do Kobo."""
    text = strip_accents(str(text))
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    if text and not text[0].isalpha():
        text = f"v_{text}"
    return text or "campo"


def normalize_type(raw: str) -> tuple[str, str | None, bool]:
    """Separa o tipo de uma linha da survey.

    Retorna ``(tipo_base, nome_da_lista, tem_or_other)``. Aceita as variações
    ``begin group``/``begin_group`` e ``select one``/``select_one``.
    """
    parts = str(raw or "").strip().split()
    if not parts:
        return "", None, False
    if len(parts) >= 2 and parts[0] in ("begin", "end") and parts[1] in ("group", "repeat"):
        return f"{parts[0]}_{parts[1]}", None, False
    if len(parts) >= 2 and parts[0] == "select" and parts[1] in ("one", "multiple"):
        parts = [f"select_{parts[1]}"] + parts[2:]
    base = parts[0]
    list_name = parts[1] if len(parts) > 1 else None
    or_other = len(parts) > 2 and parts[2] == "or_other"
    return base, list_name, or_other


@dataclass
class Row:
    sheet: str
    number: int  # número da linha no Excel (o cabeçalho é a linha 1)
    data: dict[str, str]

    def get(self, column: str, default: str = "") -> str:
        return self.data.get(column, default)

    def columns_starting(self, base: str) -> dict[str, str]:
        """Valores de ``base`` e ``base::idioma`` nesta linha."""
        return {
            k: v for k, v in self.data.items() if k == base or k.startswith(f"{base}::")
        }

    @property
    def name(self) -> str:
        # Em end_group/end_repeat o name apenas repete o do grupo; não é um campo.
        if self.base_type in GROUP_END:
            return ""
        return self.get("name")

    @property
    def type_info(self) -> tuple[str, str | None, bool]:
        return normalize_type(self.get("type"))

    @property
    def base_type(self) -> str:
        return self.type_info[0]

    @property
    def list_name(self) -> str | None:
        base, list_name, _ = self.type_info
        return list_name if base in SELECT_TYPES else None

    def has_label(self) -> bool:
        return any(v for v in self.columns_starting("label").values())


@dataclass
class Form:
    path: str
    sheets: dict[str, list[Row]] = field(default_factory=dict)
    headers: dict[str, list[str]] = field(default_factory=dict)
    # Abas com nome parecido (ex.: "Choices"), para mensagens mais úteis.
    misnamed_sheets: dict[str, str] = field(default_factory=dict)

    # ---------- construção ----------
    @classmethod
    def from_dict(cls, data: dict[str, list[dict]], path: str = "<memoria>") -> "Form":
        """Cria um formulário a partir de listas de dicionários (usado nos testes)."""
        form = cls(path=path)
        for sheet, rows in data.items():
            headers: list[str] = []
            parsed: list[Row] = []
            for i, raw in enumerate(rows, start=2):
                clean = {
                    normalize_header(k): _clean(v) for k, v in raw.items()
                }
                for h in clean:
                    if h not in headers:
                        headers.append(h)
                if any(clean.values()):
                    parsed.append(Row(sheet=sheet, number=i, data=clean))
            form.sheets[sheet] = parsed
            form.headers[sheet] = headers
        return form

    @classmethod
    def from_xlsx(cls, path: str | Path) -> "Form":
        path = Path(path)
        if not path.exists():
            raise FormReadError(f"Arquivo não encontrado: {path}")
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:  # openpyxl levanta vários tipos
            raise FormReadError(f"Não foi possível abrir '{path}' como .xlsx: {exc}") from exc

        form = cls(path=str(path))
        for ws in wb.worksheets:
            title = ws.title.strip()
            key = title.lower()
            if key not in KNOWN_SHEETS:
                continue
            if title != key:
                form.misnamed_sheets[key] = ws.title
                continue
            rows_iter = ws.iter_rows(values_only=True)
            header_row = next(rows_iter, None) or ()
            headers = [normalize_header(h) if h is not None else "" for h in header_row]
            parsed: list[Row] = []
            for number, values in enumerate(rows_iter, start=2):
                data = {
                    h: _clean(v)
                    for h, v in zip(headers, values)
                    if h
                }
                if any(data.values()):
                    parsed.append(Row(sheet=key, number=number, data=data))
            form.sheets[key] = parsed
            form.headers[key] = [h for h in headers if h]
        wb.close()
        return form

    # ---------- consultas ----------
    def has_sheet(self, name: str) -> bool:
        return name in self.sheets

    def rows(self, sheet: str) -> list[Row]:
        return self.sheets.get(sheet, [])

    @property
    def survey(self) -> list[Row]:
        return self.rows(SURVEY)

    @property
    def choices(self) -> list[Row]:
        return self.rows(CHOICES)

    @property
    def settings(self) -> dict[str, str]:
        rows = self.rows(SETTINGS)
        return rows[0].data if rows else {}

    def choice_lists(self) -> dict[str, list[Row]]:
        lists: dict[str, list[Row]] = {}
        for row in self.choices:
            name = row.get("list_name")
            if name:
                lists.setdefault(name, []).append(row)
        return lists

    def field_names(self) -> set[str]:
        return {r.name for r in self.survey if r.name}

    def languages(self, sheet: str | None = None) -> list[str]:
        """Idiomas declarados em colunas ``label::idioma``. A coluna ``label`` sem
        idioma conta como idioma padrão quando coexiste com colunas traduzidas."""
        sheets = [sheet] if sheet else [SURVEY, CHOICES]
        langs: list[str] = []
        plain = False
        for s in sheets:
            for h in self.headers.get(s, []):
                if h.startswith("label::"):
                    lang = h.split("::", 1)[1]
                    if lang not in langs:
                        langs.append(lang)
                elif h == "label":
                    plain = True
        if langs and plain:
            langs.insert(0, "")  # "" representa a coluna label sem idioma
        return langs

    def select_questions(self) -> Iterator[Row]:
        for row in self.survey:
            if row.list_name:
                yield row

    def iter_with_groups(self) -> Iterator[tuple[Row, list[Row]]]:
        """Percorre a survey devolvendo cada linha e a pilha de grupos abertos."""
        stack: list[Row] = []
        for row in self.survey:
            base = row.base_type
            if base in GROUP_END:
                if stack:
                    stack.pop()
                yield row, list(stack)
                continue
            yield row, list(stack)
            if base in GROUP_BEGIN:
                stack.append(row)


def references(expression: str) -> list[str]:
    return [m.strip() for m in REF_PATTERN.findall(expression or "")]


def _clean(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def iter_tokens(text: str) -> Iterable[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", strip_accents(text))
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def form_to_xlsx(form: Form, path):
    """Grava o formulário em .xlsx, preservando a ordem das colunas."""
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for sheet, rows in form.sheets.items():
        ws = wb.create_sheet(sheet)
        headers = form.headers.get(sheet) or sorted({k for r in rows for k in r.data})
        ws.append(headers)
        for row in rows:
            ws.append([row.data.get(h, "") or None for h in headers])
    if isinstance(path, str):
        path = Path(path)
    wb.save(path)  # aceita caminho ou arquivo em memória (BytesIO)
    return path
