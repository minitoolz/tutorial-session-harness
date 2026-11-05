"""End-to-end tests for the tutor CLI against a throwaway project root."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from tutor import build as build_mod
from tutor.cli import main

REPO = Path(__file__).resolve().parent.parent

AUDIENCE_OK = """\
audience:
  field: "computer vision engineering"
  background: "MS in EE, 4 years ML engineer"
  strong_in: ["PyTorch", "linear algebra"]
  weak_in: ["probability"]
  math_level: "calculus and linear algebra"
  familiar_domains: ["image processing"]
  goals: "read diffusion papers"
"""


def write_settings(root: Path, audience: str = AUDIENCE_OK, extra: str = "") -> None:
    (root / "SETTINGS.md").write_text(
        f"---\n{audience}language: en\nstyle: article\n{extra}---\n\n# Preferences\n- examples first\n",
        encoding="utf-8",
    )


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "topics").mkdir()
    shutil.copy(REPO / "AGENTS.md", tmp_path / "AGENTS.md")
    shutil.copy(REPO / "SETTINGS.example.md", tmp_path / "SETTINGS.example.md")
    shutil.copytree(REPO / "skills", tmp_path / "skills")
    monkeypatch.setenv("TUTOR_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def ready(root):
    write_settings(root)
    assert main(["start"]) == 0
    return root


@pytest.fixture
def topic(ready):
    assert main(["new", "demo"]) == 0
    t = ready / "topics" / "demo"
    (t / "abstract.md").write_text("A short abstract with $x^2$.\n", encoding="utf-8")
    (t / "intro.md").write_text("# Introduction\n\nWe study **softmax** here.\n", encoding="utf-8")
    (t / "index.md").write_text("# Contents\n\n1. [Definition](definition.md)\n", encoding="utf-8")
    (t / "definition.md").write_text(
        "# Definition\n\nThe **logit** is a raw score.\n\n"
        "$$\np_i = \\frac{e^{z_i}}{\\sum_j e^{z_j}} \\label{eq:sm}\n$$\n\n"
        "See \\eqref{eq:sm}. Water is H<sub>2</sub>O.\n\n"
        "$$\nq = z^2 \\label{eq:q}\n$$\n\nSee \\eqref{eq:q}.\n\n$$ r = 1 $$\n\n"
        "$$\n\\begin{align}\na &= b \\label{eq:ab} \\\\\nc &= d\n\\end{align}\n$$\n\n"
        "<table>\n<tr><th>name</th><th>value</th></tr>\n<tr><td>**fp32**</td><td>$x^2$</td></tr>\n</table>\n",
        encoding="utf-8",
    )
    (t / "glossary.md").write_text(
        "# Glossary\n\nLogit\n:   A raw class score before softmax.\n\n"
        "Softmax\n:   Turns logits into probabilities.\n",
        encoding="utf-8",
    )
    return t


def out(capsys) -> str:
    c = capsys.readouterr()
    return c.out + c.err


# ── settings gate / onboarding ──────────────────────────────────────────────

def test_missing_settings_requires_onboarding(root, capsys):
    assert main(["start"]) == 2
    assert "ONBOARDING REQUIRED" in out(capsys)
    assert main(["new", "x"]) == 1
    assert "ONBOARDING REQUIRED" in out(capsys)


def test_example_copied_verbatim_still_requires_onboarding(root, capsys):
    shutil.copy(root / "SETTINGS.example.md", root / "SETTINGS.md")
    assert main(["start"]) == 2
    assert "audience fields missing" in out(capsys)


def test_changed_settings_must_be_reread(ready, capsys):
    write_settings(ready, extra="fontsize: 12pt\n")
    assert main(["new", "x"]) == 1
    assert "SETTINGS NOT READ" in out(capsys)
    assert main(["start"]) == 0
    assert main(["new", "x"]) == 0


# ── topics / order ──────────────────────────────────────────────────────────

def test_new_topic_skeleton(ready):
    assert main(["new", "attention-basics", "--title", "Attention"]) == 0
    t = ready / "topics" / "attention-basics"
    for f in ("abstract.md", "intro.md", "index.md", "glossary.md", "topic.yaml", "imgs", "codes"):
        assert (t / f).exists()
    assert 'title: "Attention"' in (t / "topic.yaml").read_text()
    assert "order" not in yaml.safe_load((t / "topic.yaml").read_text())
    assert main(["lint", "attention-basics"]) == 0  # a fresh topic lints clean


def test_topic_name_must_be_kebab(ready, capsys):
    assert main(["new", "Bad_Name"]) == 1
    assert "kebab-case" in out(capsys)


def test_order_follows_index(topic, capsys):
    (topic / "appendix.md").write_text("# Appendix\n")
    (topic / "index.md").write_text(
        "# Contents\n\n<!-- 1. [Ignored](ignored.md) -->\n"
        "1. [Appendix](appendix.md)\n2. [Definition](definition.md)\n", encoding="utf-8")
    assert main(["order", "demo"]) == 0
    assert out(capsys).split()[:10] == ["1.", "abstract.md", "2.", "intro.md", "3.", "appendix.md",
                                        "4.", "definition.md", "5.", "glossary.md"]


def test_migrate_splits_contents_into_section_pages(topic, capsys):
    (topic / "index.md").unlink()
    (topic / "definition.md").unlink()
    (topic / "topic.yaml").write_text(
        (topic / "topic.yaml").read_text() + "order:\n  - abstract.md\n  - contents.md\n")
    (topic / "imgs" / "contents-plot.png").write_bytes(b"x")
    (topic / "contents.md").write_text(
        "<!-- template comment -->\n# Logits {#sec:logits}\n\nThe **logit** is a raw score.\n\n"
        "```python\n# not a heading\n```\n\n"
        "# Softmax\n\nWe study **softmax**. ![p](imgs/contents-plot.png)\n", encoding="utf-8")
    assert main(["lint", "demo"]) == 1
    assert "tutor migrate" in out(capsys)
    assert main(["migrate", "demo"]) == 0
    assert not (topic / "contents.md").exists()
    assert (topic / "index.md").read_text() == "# Contents\n\n1. [Logits](logits.md)\n2. [Softmax](softmax.md)\n"
    assert "# not a heading" in (topic / "logits.md").read_text()
    assert "imgs/softmax-plot.png" in (topic / "softmax.md").read_text()
    assert (topic / "imgs" / "softmax-plot.png").exists()
    assert "order" not in yaml.safe_load((topic / "topic.yaml").read_text())
    capsys.readouterr()
    assert main(["lint", "demo"]) == 0


# ── lint ────────────────────────────────────────────────────────────────────

def test_lint_clean(topic, capsys):
    assert main(["lint", "demo"]) == 0
    assert "0 error(s)" in out(capsys)


def test_lint_image_naming_and_references(topic, capsys):
    (topic / "imgs" / "Figure1.png").write_bytes(b"x")
    (topic / "imgs" / "definition-ok.png").write_bytes(b"x")
    with (topic / "definition.md").open("a") as f:
        f.write("\n![a](imgs/definition-ok.png)\n![b](imgs/definition-missing.png)\n")
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "imgs/Figure1.png" in o and "{pagename}-{short-name}" in o
    assert "definition-missing.png' does not exist" in o
    assert "definition-ok.png" not in o


def test_lint_index_must_match_pages(topic, capsys):
    (topic / "extra.md").write_text("# Extra\n")
    with (topic / "index.md").open("a") as f:
        f.write("2. [Gone](gone.md)\n3. [Again](definition.md)\n4. [Intro](intro.md)\n")
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "extra.md  page is not listed in index.md" in o
    assert "'gone.md' does not exist" in o
    assert "'definition.md' is listed twice" in o
    assert "'intro.md' has a fixed place" in o


def test_lint_unbalanced_math(topic, capsys):
    with (topic / "definition.md").open("a") as f:
        f.write("\nBroken $x + y here.\n")
    assert main(["lint", "demo"]) == 1
    assert "unbalanced inline math" in out(capsys)


def test_lint_warns_on_bare_math_environment(topic, capsys):
    with (topic / "definition.md").open("a") as f:
        f.write("\n\\begin{equation}\nx = 1 \\label{eq:bare}\n\\end{equation}\n")
    assert main(["lint", "demo"]) == 0  # a warning, not an error
    assert "outside $$" in out(capsys)


def test_glossary_is_required(topic, capsys):
    (topic / "glossary.md").unlink()
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "glossary.md" in o and "required page is missing" in o


def test_glossary_consistency(topic, capsys):
    with (topic / "definition.md").open("a") as f:
        f.write("\nA <dfn>temperature</dfn> divides the logits.\n")
    (topic / "glossary.md").write_text(
        "# Glossary\n\nLogit\n:   score\n\nLogit\n:   again\n\n"
        "Softmax\n:   probs\n\n어텐션 (attention)\n:   never used here\n",
        encoding="utf-8",
    )
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "duplicate entry 'Logit'" in o
    assert "'temperature' is marked as a definition but has no entry in glossary.md" in o
    assert "'어텐션 (attention)' is not used in any page" in o
    assert "'softmax' is marked" not in o  # intro bolds **softmax**; glossary has it


# ── review ──────────────────────────────────────────────────────────────────

BAD = """# Bad

Since the normalizer couples every logit which means the gradient of each output with respect to any input involves all of the others as discussed above, temperature scaling changes the effective learning rate.

학습 중에 버그를 밟았다. These results were measured on the host machine and may not apply to other GPUs.

| | E1 | E2 | E3 |
|---|---|---|---|
| top-1 | 76.1 | 79.4 | 80.2 |

The L1 and L2 norms on an A100 and an H100 are fine.
"""


def test_review_flags_each_problem(topic, capsys):
    (topic / "definition.md").write_text(BAD, encoding="utf-8")
    assert main(["review", "demo", "definition.md"]) == 0
    o = out(capsys)
    for tag in ("[long-sentence]", "[phrase] '버그를 밟'", "[hedge] 'may not apply'", "[opaque-label] E1, E2, E3"):
        assert tag in o, tag
    assert "L1" not in o and "A100" not in o
    assert main(["review", "demo", "definition.md", "--strict"]) == 1


def test_review_undefined_term(topic, capsys):
    (topic / "intro.md").write_text("# Intro\n\nWe use the logit a lot.\n", encoding="utf-8")
    main(["review", "demo"])
    assert "[undefined-term] 'logit'" in out(capsys)


def test_review_local_phrases(topic, capsys):
    local = topic.parent.parent / "skills.local" / "clear-writing"
    local.mkdir(parents=True)
    (local / "phrases.yaml").write_text('phrases:\n  - pattern: "raw score"\n    why: "confused me"\n')
    main(["review", "demo"])
    assert "[phrase] 'raw score' — confused me" in out(capsys)


# ── build ───────────────────────────────────────────────────────────────────

def test_build_html_preview(topic, capsys):
    assert main(["build", "demo", "--html"]) == 0
    html = (topic / "build" / "demo.html").read_text(encoding="utf-8")
    assert "<math" in html and "<table" in html and "<sub>2</sub>" in html
    assert "\\label" not in html  # labelled $$ math renders without the raw label
    assert "A short abstract" in html  # abstract.md → abstract block


@pytest.mark.skipif(not build_mod.xelatex_available(), reason="xelatex not installed")
@pytest.mark.parametrize("style", build_mod.styles())
def test_build_pdf(topic, style):
    assert main(["build", "demo", "--style", style]) == 0
    pdf = topic / "build" / "demo.pdf"
    assert pdf.read_bytes()[:4] == b"%PDF"


@pytest.mark.skipif(not build_mod.xelatex_available(), reason="xelatex not installed")
def test_html_survives_into_latex(topic):
    import subprocess

    tex = subprocess.run(
        [build_mod.pandoc_bin(), "definition.md", "-f", "markdown", "-t", "latex",
         "--lua-filter", str(build_mod.data_path("pandoc", "html2latex.lua"))],
        cwd=topic, capture_output=True, text=True, check=True,
    ).stdout
    assert "\\textsubscript{2}" in tex
    assert "\\textbf{fp32} & \\(x^2\\)" in tex
    assert "\\label{eq:sm}" in tex
    # labelled $$ math becomes a numbered equation; unlabelled stays unnumbered
    assert "\\begin{equation}\nq = z^2 \\label{eq:q}\n\\end{equation}" in tex
    assert re.search(r"\\\[\s*r = 1\s*\\\]", tex)
    # $$ around align: the align environment itself, not nested in \[ ... \]
    assert "\\begin{align}\na &= b \\label{eq:ab}" in tex
    assert "\\[\\begin{align}" not in tex and "\\begin{equation}\n\\begin{align}" not in tex
