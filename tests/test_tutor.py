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

Since the normalizer couples every logit which means the gradient of each output with respect to any input involves all of the others as discussed above, temperature scaling, which divides every logit by a single positive number before the exponential is taken, changes not only the entropy of the output distribution but also the effective learning rate of all the upstream layers.

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


def test_review_sentence_limit_allows_moderate_sentences(topic, capsys):
    words = " ".join(["word"] * 40)
    (topic / "definition.md").write_text(f"# D\n\nA {words}.\n", encoding="utf-8")
    main(["review", "demo", "definition.md"])
    assert "[long-sentence]" not in out(capsys)  # 41 words is under the default of 50


UNLINKED = "# D\n\nPaDiM fits a Gaussian per position. Objects rotate in many datasets. PatchCore drops position. Memory banks grow large.\n"
LINKED = ("# D\n\nPaDiM fits a Gaussian per position. So it assumes aligned objects. "
          "However, objects rotate in many datasets. For example, screws lie at random angles.\n")
LINKED_KO = ("# D\n\nPaDiM은 위치마다 Gaussian을 추정한다. 그래서 정렬된 물체를 가정한다. "
             "반면 PatchCore는 위치를 버린다. 이 방식은 회전한 물체에도 맞는다.\n")


@pytest.mark.parametrize("text, flagged", [(UNLINKED, True), (LINKED, False), (LINKED_KO, False)])
def test_review_low_cohesion(topic, capsys, text, flagged):
    (topic / "definition.md").write_text(text, encoding="utf-8")
    main(["review", "demo", "definition.md"])
    assert ("[low-cohesion]" in out(capsys)) is flagged


def test_review_low_cohesion_skips_captions_and_glossary(topic, capsys):
    caption = "<figcaption>Lineage. Solid lines inherit ideas. Dashed lines are later work.</figcaption>"
    (topic / "definition.md").write_text(f"# D\n\n<figure>\n{caption}\n</figure>\n", encoding="utf-8")
    (topic / "glossary.md").write_text(
        "# Glossary\n\nLogit\n:   A raw score. It is not a probability. Softmax normalizes it.\n",
        encoding="utf-8",
    )
    main(["review", "demo"])
    assert "[low-cohesion]" not in out(capsys)


def test_review_low_cohesion_can_be_disabled(ready, capsys):
    write_settings(ready, extra="review:\n  max_unlinked_sentences: -1\n")
    assert main(["start"]) == 0
    assert main(["new", "demo"]) == 0
    (ready / "topics" / "demo" / "intro.md").write_text(UNLINKED, encoding="utf-8")
    capsys.readouterr()
    main(["review", "demo", "intro.md"])
    assert "[low-cohesion]" not in out(capsys)


def test_review_agreement_lists_copula_pairs(topic, capsys):
    (topic / "definition.md").write_text(
        "# D\n\n게다가 판정은 여전히 Gaussian 거리이므로, 경계를 직접 만들지는 않는다. "
        "Wall Plugs에서는 물체가 겹친다. The decision is a distance.\n",
        encoding="utf-8",
    )
    assert main(["review", "demo", "definition.md", "--agreement"]) == 0
    o = out(capsys)
    assert "[agreement] 판정 → 거리이므로" in o
    assert "[agreement] decision → distance" in o
    assert "Plugs에서" not in o  # locative "~에서는" is not a subject
    assert "[long-sentence]" not in o  # the audit replaces the normal review output


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


@pytest.mark.skipif(not build_mod.xelatex_available(), reason="xelatex not installed")
def test_refs_survive_inside_html_blocks(tmp_path):
    import subprocess

    (tmp_path / "page.md").write_text(
        "$$ x = 1 \\label{eq:a} $$\n\n"
        "<figure>\n<img src=\"imgs/x.png\" width=\"100%\">\n"
        "<figcaption>식 \\eqref{eq:a}의 flow, $y$, 그림 \\ref{fig:b}.</figcaption>\n</figure>\n\n"
        "<table><tr><td>see \\eqref{eq:a}</td></tr></table>\n",
        encoding="utf-8",
    )

    def run(fmt):
        return subprocess.run(
            [build_mod.pandoc_bin(), "page.md", "-f", "markdown", "-t", fmt,
             "--lua-filter", str(build_mod.data_path("pandoc", "html2latex.lua"))],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout

    tex = run("latex")
    assert "\\caption{식 \\eqref{eq:a}의 flow, \\(y\\), 그림 \\ref{fig:b}.}" in tex
    assert "see \\eqref{eq:a}" in tex
    html = run("html")  # preview: refs show as plain text, no crash
    assert "식 (eq:a)의 flow" in html and "see (eq:a)" in html


MERMAID_PAGE = (
    "# Flow\n\nThe pipeline:\n\n"
    "```{.mermaid #fig:flow caption=\"Inspection flow\" width=\"60%\"}\n"
    "flowchart LR\n  A[Image] --> B{Defect?}\n  B -->|yes| C[Reject]\n  B -->|no| D[Pass]\n```\n\n"
    "```mermaid\nsequenceDiagram\n  Camera->>Model: frame\n```\n"
)


def _add_mermaid_page(topic):
    (topic / "flow.md").write_text(MERMAID_PAGE, encoding="utf-8")
    with (topic / "index.md").open("a") as f:
        f.write("2. [Flow](flow.md)\n")


def test_build_without_mmdc_explains_install(topic, capsys, monkeypatch):
    _add_mermaid_page(topic)
    monkeypatch.setattr(build_mod, "mmdc_bin", lambda: None)
    assert main(["build", "demo", "--html"]) == 1
    assert "npm install -g @mermaid-js/mermaid-cli" in capsys.readouterr().err


@pytest.mark.skipif(not build_mod.mmdc_bin(), reason="mermaid-cli (mmdc) not installed")
def test_build_renders_mermaid(topic, capsys):
    _add_mermaid_page(topic)
    assert main(["build", "demo", "--html"]) == 0
    html = (topic / "build" / "demo.html").read_text(encoding="utf-8")
    assert "Inspection flow" in html and "flowchart LR" not in html
    assert len(list((topic / "build" / "mermaid").glob("*.svg"))) == 2
    if build_mod.xelatex_available():
        assert main(["build", "demo"]) == 0
        assert len(list((topic / "build" / "mermaid").glob("*.pdf"))) == 2


# ── terms: one written form per technical term ──────────────────────────────

def test_lint_flags_avoided_term_forms(topic, capsys):
    (topic.parent.parent / "terms.yaml").write_text(
        "layer: [neural network layer, 층, 레이어, couche]\n注意力: [attention]\n", encoding="utf-8")
    with (topic / "definition.md").open("a") as f:
        f.write("\nEach neural network layers stack. 레이어는 계층의 일부다. Une couche. "
                "Code `레이어` and math $층$ are fine. A layer is fine.\n")
    assert main(["lint", "demo"]) == 1
    o = out(capsys)
    assert "[term] 'neural network layers': write 'layer'" in o
    assert "[term] '레이어는': write 'layer'" in o
    assert "[term] 'couche': write 'layer'" in o
    assert "계층" not in o and "[term] '층'" not in o and "'attention'" not in o


def test_terms_command_checks_every_topic_and_start_prints_them(topic, capsys):
    root = topic.parent.parent
    (root / "terms.yaml").write_text("logit: [로짓, raw score]\n", encoding="utf-8")
    assert main(["start"]) == 0
    assert "logit   (not: 로짓, raw score)" in out(capsys)
    assert main(["new", "other"]) == 0
    (root / "topics" / "other" / "intro.md").write_text("# Intro\n\n로짓을 본다.\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["terms"]) == 1
    o = out(capsys)
    assert "terms demo" in o and "'raw score'" in o      # demo's definition.md
    assert "terms other" in o and "'로짓을'" in o


def test_terms_yaml_contradictions(topic, capsys):
    (topic.parent.parent / "terms.yaml").write_text("layer: [층]\n층: [floor]\n", encoding="utf-8")
    assert main(["lint", "demo"]) == 1
    assert "'층' is both a term to write and a form to avoid" in out(capsys)
