"""Monta a versão web (pasta site/) para publicar no GitHub Pages.

A versão web roda o mesmo validador Python dentro do navegador, com Pyodide.
Tudo o que a página precisa é servido pelo próprio site (nenhum CDN externo),
então o arquivo do usuário nunca sai do computador dele.

Uso:
    python scripts/build_web.py            # gera site/
    python -m http.server -d site 8000     # testa em http://localhost:8000
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"

PYODIDE_VERSION = "0.29.5"
PYODIDE_URL = f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz"
PYODIDE_FILES = [
    "pyodide.js", "pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm",
    "python_stdlib.zip", "pyodide-lock.json",
]
# Dependências Python puras (sem código compilado), testadas no Pyodide.
WHEELS = [
    "pyxform==4.5.0",
    "openpyxl==3.1.5",
    "et_xmlfile==2.0.0",
    "lark==1.3.1",
    "defusedxml==0.7.1",
    "xlrd==2.0.1",
]


def download(url: str, target: Path) -> Path:
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"baixando {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            target.write_bytes(resp.read())
    except Exception:
        subprocess.run(["curl", "-sSfL", "-o", str(target), url], check=True)
    return target


def add_pyodide(site: Path) -> None:
    tgz = download(PYODIDE_URL, CACHE / f"pyodide-{PYODIDE_VERSION}.tgz")
    dest = site / "pyodide"
    dest.mkdir(parents=True)
    with tarfile.open(tgz) as tar:
        for name in PYODIDE_FILES:
            member = tar.getmember(f"package/{name}")
            (dest / name).write_bytes(tar.extractfile(member).read())


def add_wheels(site: Path) -> list[str]:
    cache = CACHE / "wheels"
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "download", "--quiet", "--only-binary=:all:", "--no-deps",
         "--dest", str(cache), *WHEELS],
        check=True,
    )
    dest = site / "wheels"
    dest.mkdir(parents=True)
    names = []
    for spec in WHEELS:
        project, version = spec.split("==")
        prefix = f"{project.replace('-', '_').lower()}-{version}-"
        match = next(p for p in cache.glob("*.whl") if p.name.lower().startswith(prefix))
        shutil.copy2(match, dest / match.name)
        names.append(match.name)
    return names


def add_app(site: Path) -> None:
    package = ROOT / "src" / "xlsform_validator"
    with zipfile.ZipFile(site / "app.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(package.parent))
    rules = yaml.safe_load((package / "rules.yaml").read_text(encoding="utf-8"))
    (site / "rules.json").write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")


def build(site: Path) -> None:
    if site.exists():
        shutil.rmtree(site)
    shutil.copytree(ROOT / "web", site)
    (site / ".nojekyll").write_text("")
    # imagem de prévia social (og:image), mesma de docs/ no repositório
    shutil.copy2(ROOT / "docs" / "social-preview.png", site / "social-preview.png")
    add_pyodide(site)
    wheels = add_wheels(site)
    add_app(site)
    examples = site / "exemplos"
    examples.mkdir()
    for name in ("abrigo_bom.xlsx", "abrigo_ruim.xlsx"):
        shutil.copy2(ROOT / "examples" / name, examples / name)
    manifest = {
        "pyodide": PYODIDE_VERSION,
        "wheels": wheels,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (site / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    size = sum(p.stat().st_size for p in site.rglob("*") if p.is_file()) / 1e6
    print(f"site gerado em {site.relative_to(ROOT)} ({size:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saida", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    build(args.saida.resolve())
