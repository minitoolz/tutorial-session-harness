"""Bold math (\\bm, \\boldsymbol, \\mathbf on Greek) must build under XeLaTeX + unicode-math."""
from __future__ import annotations

import subprocess

import pytest

from tutor import build as build_mod

BOLD_MATH = "# Bold\n\n$$\\bm{\\mu} + \\boldsymbol{\\epsilon} + \\bm{x} + \\mathbf{\\Sigma} + \\mathbf{x}$$\n"


@pytest.mark.skipif(not build_mod.xelatex_available(), reason="xelatex not installed")
@pytest.mark.parametrize("style", build_mod.styles())
def test_bold_math_builds_in_every_style(tmp_path, style):
    src = tmp_path / "bold.md"
    src.write_text(BOLD_MATH, encoding="utf-8")
    pdf = tmp_path / "bold.pdf"
    proc = subprocess.run(
        [build_mod.pandoc_bin(), str(src), "-o", str(pdf), "--pdf-engine=xelatex",
         "-M", "title=Bold", "-H", str(build_mod.data_path("pandoc", "styles", f"{style}.tex"))],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert pdf.read_bytes()[:4] == b"%PDF"
    # \mathbf on Greek used to fall back to the text font and silently drop the glyph
    assert "Missing character" not in proc.stderr
