"""PDF / HTML build via pandoc (+ XeLaTeX)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from importlib import resources
from pathlib import Path

import yaml

from .settings import Settings, TutorError
from .topic import Topic

CJK_LANGS = ("ko", "ja", "zh")
TEX_FALLBACK_DIRS = ("/Library/TeX/texbin", "/usr/local/texlive/bin", "/usr/texbin")


def data_path(*parts: str) -> Path:
    return Path(str(resources.files("tutor").joinpath("data", *parts)))


def styles() -> list[str]:
    return sorted(p.stem for p in data_path("pandoc", "styles").glob("*.tex"))


def pandoc_bin() -> str:
    try:
        import pypandoc

        return pypandoc.get_pandoc_path()
    except (ImportError, OSError):
        found = shutil.which("pandoc")
        if not found:
            raise TutorError("pandoc not found. Run `uv sync` (installs pypandoc-binary).")
        return found


def tex_env() -> dict:
    env = dict(os.environ)
    if not shutil.which("xelatex", path=env.get("PATH")):
        extra = [d for d in TEX_FALLBACK_DIRS if Path(d, "xelatex").exists()]
        env["PATH"] = os.pathsep.join([*extra, env.get("PATH", "")])
    return env


MERMAID_FENCE_RE = re.compile(r"^\s*(```|~~~)\s*(mermaid\b|\{[^}]*\.mermaid\b)", re.M)
MMDC_INSTALL = (
    "Install mermaid-cli (MIT license, needs Node.js): `npm install -g @mermaid-js/mermaid-cli`, "
    "or set TUTOR_MMDC to an mmdc binary."
)


def mmdc_bin() -> str | None:
    """mermaid-cli: $TUTOR_MMDC if set, else `mmdc` on PATH."""
    env = os.environ.get("TUTOR_MMDC")
    if env:
        return env if Path(env).is_file() else None
    return shutil.which("mmdc")


def uses_mermaid(topic: Topic, pages: list[str]) -> bool:
    return any(MERMAID_FENCE_RE.search((topic.path / p).read_text(encoding="utf-8")) for p in pages)


def xelatex_available() -> bool:
    return shutil.which("xelatex", path=tex_env()["PATH"]) is not None


def _abstract_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
    text = re.sub(r"^#\s+.*\n?", "", text).strip()  # template prints its own "Abstract"
    return text


def build(topic: Topic, settings: Settings, style: str | None = None, html: bool = False) -> Path:
    style = style or settings.style
    if style not in styles():
        raise TutorError(f"Unknown style '{style}'. Available: {', '.join(styles())}")
    order = topic.order()
    missing = [p for p in order if not (topic.path / p).is_file()]
    if missing:
        raise TutorError(f"missing pages: {missing}. Run `uv run tutor lint`.")

    meta = settings.pandoc_metadata()
    tmeta = topic.meta()
    for key in ("title", "subtitle", "author", "date"):
        if tmeta.get(key):
            meta[key] = tmeta[key]
    lang = str(meta.get("lang", ""))
    if lang[:2] in CJK_LANGS and not meta.get("CJKmainfont"):
        raise TutorError(
            f"language '{lang}' needs `CJKmainfont` in SETTINGS.md (e.g. 'Noto Serif CJK KR' or "
            "'Apple SD Gothic Neo'). Check installed fonts with `fc-list :lang=ko family`."
        )

    inputs = list(order)
    if "abstract.md" in inputs:
        abstract = _abstract_text(topic.path / "abstract.md")
        inputs.remove("abstract.md")
        if abstract:
            meta["abstract"] = abstract

    topic.build_dir.mkdir(exist_ok=True)
    meta_file = topic.build_dir / f"{topic.name}.meta.yaml"
    meta_file.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")

    ext = "html" if html else "pdf"
    out = topic.build_dir / f"{topic.name}.{ext}"
    cmd = [
        pandoc_bin(), *inputs,
        "--defaults", str(data_path("pandoc", "defaults.yaml")),
        "--metadata-file", str(meta_file),
        "--lua-filter", str(data_path("pandoc", "html2latex.lua")),
        "--resource-path", ".",
        "-o", str(out),
    ]
    if html:
        cmd += ["-t", "html5", "--mathml", "--embed-resources",
                "--css", str(data_path("pandoc", "preview.css"))]
    else:
        if not xelatex_available():
            raise TutorError(
                "xelatex not found. Install a TeX distribution (macOS: `brew install --cask mactex-no-gui`; "
                "Debian/Ubuntu: `apt install texlive-xetex texlive-latex-extra texlive-lang-cjk`)."
            )
        cmd += ["-H", str(data_path("pandoc", "styles", f"{style}.tex"))]

    env = tex_env()
    if uses_mermaid(topic, order):
        mmdc = mmdc_bin()
        if not mmdc:
            raise TutorError("This topic has mermaid diagrams, but mermaid-cli (mmdc) was not found. "
                             + MMDC_INSTALL)
        (topic.build_dir / "mermaid").mkdir(exist_ok=True)
        env["TUTOR_MMDC"] = mmdc
        env["TUTOR_MERMAID_DIR"] = "build/mermaid"  # relative to the topic folder (pandoc's cwd)

    proc = subprocess.run(cmd, cwd=topic.path, env=env, capture_output=True, text=True)
    if proc.stderr.strip():
        print(proc.stderr.strip())
    if proc.returncode != 0:
        raise TutorError(f"pandoc failed (exit {proc.returncode}). See messages above.")
    return out
