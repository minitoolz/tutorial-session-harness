"""End-to-end tests for the tutor CLI against a throwaway project root."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

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
    (t / "contents.md").write_text(
        "# Definition\n\nThe **logit** is a raw score.\n\n"
        "\\begin{equation}\np_i = \\frac{e^{z_i}}{\\sum_j e^{z_j}} \\label{eq:sm}\n\\end{equation}\n\n"
        "See \\eqref{eq:sm}. Water is H<sub>2</sub>O.\n\n"
        "$$\nq = z^2 \\label{eq:q}\n$$\n\nSee \\eqref{eq:q}.\n\n$$ r = 1 $$\n\n"
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
    for f in ("abstract.md", "intro.md", "contents.md", "glossary.md", "topic.yaml", "imgs", "codes"):
        assert (t / f).exists()
    assert 'title: "Attention"' in (t / "topic.yaml").read_text()


def test_topic_name_must_be_kebab(ready, capsys):
    assert main(["new", "Bad_Name"]) == 1
    assert "kebab-case" in out(capsys)


def test_order_reset_puts_paper_pages_first_glossary_last(topic, capsys):
    (topic / "appendix.md").write_text("# Appendix\n")
    assert main(["order", "demo", "--reset"]) == 0
    assert out(capsys).split() == ["1.", "abstract.md", "2.", "intro.md", "3.", "contents.md",
                                   "4.", "appendix.md", "5.", "glossary.md"]


# ── lint ────────────────────────────────────────────────────────────────────

def test_lint_clean(topic, capsys):
    assert main(["lint", "demo"]) == 0
    assert "0 error(s)" in out(capsys)


def test_lint_image_naming_and_references(topic, capsys):
    (topic / "imgs" / "Figure1.png").write_bytes(b"x")
    (topic / "imgs" / "contents-ok.png").write_bytes(b"x")
    with (topic / "contents.md").open("a") as f:
        f.write("\n![a](imgs/contents-ok.png)\n![b](imgs/contents-missing.png)\n")
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "imgs/Figure1.png" in o and "{pagename}-{short-name}" in o
    assert "contents-missing.png' does not exist" in o
    assert "contents-ok.png" not in o


def test_lint_order_mismatch(topic, capsys):
    (topic / "extra.md").write_text("# Extra\n")
    assert main(["lint", "demo"]) == 1
    assert "'extra.md' exists but is not in order" in out(capsys)


def test_lint_unbalanced_math(topic, capsys):
    with (topic / "contents.md").open("a") as f:
        f.write("\nBroken $x + y here.\n")
    assert main(["lint", "demo"]) == 1
    assert "unbalanced inline math" in out(capsys)


def test_glossary_is_required(topic, capsys):
    (topic / "glossary.md").unlink()
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "glossary.md" in o and "required page is missing" in o


def test_glossary_consistency(topic, capsys):
    with (topic / "contents.md").open("a") as f:
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
    (topic / "contents.md").write_text(BAD, encoding="utf-8")
    assert main(["review", "demo", "contents.md"]) == 0
    o = out(capsys)
    for tag in ("[long-sentence]", "[phrase] '버그를 밟'", "[hedge] 'may not apply'", "[opaque-label] E1, E2, E3"):
        assert tag in o, tag
    assert "L1" not in o and "A100" not in o
    assert main(["review", "demo", "contents.md", "--strict"]) == 1


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
        [build_mod.pandoc_bin(), "contents.md", "-f", "markdown", "-t", "latex",
         "--lua-filter", str(build_mod.data_path("pandoc", "html2latex.lua"))],
        cwd=topic, capture_output=True, text=True, check=True,
    ).stdout
    assert "\\textsubscript{2}" in tex
    assert "\\textbf{fp32} & \\(x^2\\)" in tex
    assert "\\label{eq:sm}" in tex
    # labelled $$ math becomes a numbered equation; unlabelled stays unnumbered
    assert "\\begin{equation}\nq = z^2 \\label{eq:q}\n\\end{equation}" in tex
    assert re.search(r"\\\[\s*r = 1\s*\\\]", tex)
