"""
Gera docs/validacao_qualitativa.docx nativamente (python-docx), com aparência de
documento acadêmico comum: Arial, preto, tabelas do Word, sem emoji.

Junta docs/qualitative_analysis.md (corpo) + docs/qualitative_dataset.md (apêndice).

Uso:
    python build_qualitative_docx.py
"""
import re

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ANALYSIS = "docs/qualitative_analysis.md"
DATASET = "docs/qualitative_dataset.md"
OUT = "docs/validacao_qualitativa.docx"

BLACK = RGBColor(0, 0, 0)
FONT = "Arial"
BODY_PT = 12
H_SIZES = {1: 18, 2: 15, 3: 13, 4: 12}

# Substituições de emoji -> texto (ordem importa)
EMOJI_BOLD = [("✅ **", "**"), ("⚠️ **", "**"), ("❌ **", "**")]
EMOJI_WORD = [("✅", "Coerente"), ("⚠️", "Parcial"), ("❌", "Falso positivo")]
CLEANUPS = [
    ("Coerente Coerentes", "Coerentes"),
    ("Coerente Relevantes", "Relevantes"),
    ("marcados Parcial", "marcados como “Parcial”"),
    ("marcados com Parcial", "marcados como “Parcial”"),
]


def clean_text(t: str) -> str:
    for a, b in EMOJI_BOLD:
        t = t.replace(a, b)
    for a, b in EMOJI_WORD:
        t = t.replace(a, b)
    for a, b in CLEANUPS:
        t = t.replace(a, b)
    return t


INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)")


def add_runs(paragraph, text, bold=False, italic=False):
    """Adiciona runs aplicando **negrito**, *itálico* e `mono` (com aninhamento)."""
    for tok in INLINE_RE.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            add_runs(paragraph, tok[2:-2], bold=True, italic=italic)
        elif tok.startswith("*") and tok.endswith("*"):
            add_runs(paragraph, tok[1:-1], bold=bold, italic=True)
        elif tok.startswith("`") and tok.endswith("`"):
            # termos técnicos (nomes de função, lances, FEN): mesmo Arial/tamanho, em itálico
            r = paragraph.add_run(tok[1:-1])
            r.bold = bold; r.italic = True
        else:
            r = paragraph.add_run(tok)
            r.bold = bold; r.italic = italic


def set_cell_shading(cell, hex_color):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(sh)


def add_heading(doc, level, text):
    p = doc.add_paragraph()
    p.space_before = Pt(12)
    add_runs(p, text)
    for r in p.runs:
        r.bold = True
        r.font.size = Pt(H_SIZES[level])
    p.paragraph_format.space_before = Pt(14 if level <= 2 else 8)
    p.paragraph_format.space_after = Pt(4)
    return p


def add_hr(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "999999")
    pbdr.append(bottom); pPr.append(pbdr)


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for j, cell_text in enumerate(header):
        c = t.rows[0].cells[j]
        c.paragraphs[0].text = ""
        add_runs(c.paragraphs[0], cell_text)
        for r in c.paragraphs[0].runs:
            r.bold = True
        set_cell_shading(c, "D9D9D9")
    for row in body:
        cells = t.add_row().cells
        for j, cell_text in enumerate(row):
            if j < len(cells):
                cells[j].paragraphs[0].text = ""
                add_runs(cells[j].paragraphs[0], cell_text)
    doc.add_paragraph()


def parse_table(lines, i):
    """Lê um bloco de tabela markdown a partir de lines[i]. Retorna (rows, next_i)."""
    rows = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        raw = lines[i].strip().strip("|")
        cells = [c.strip() for c in raw.split("|")]
        if not re.match(r"^[\s:\-]+$", "".join(cells)):  # pula linha separadora ---
            rows.append(cells)
        i += 1
    return rows, i


def is_special(s):
    """Linha que inicia um bloco próprio (não é continuação de parágrafo)."""
    s = s.strip()
    return (not s or s.startswith("|") or s.startswith("#") or s.startswith(">")
            or s == "---" or s.startswith("- ") or s.startswith("* ")
            or bool(re.match(r"^\d+\.\s", s)))


def gather_continuation(lines, i):
    """Junta lines[i] com as linhas seguintes que são continuação do mesmo parágrafo."""
    parts = [lines[i].strip()]
    i += 1
    while i < len(lines) and not is_special(lines[i]):
        parts.append(lines[i].strip())
        i += 1
    return " ".join(parts), i


def style_runs(p):
    for r in p.runs:
        r.font.name = FONT; r.font.size = Pt(BODY_PT)


def render_md(doc, path, page_break_before=False):
    if page_break_before:
        doc.add_page_break()
    lines = open(path, encoding="utf-8").read().splitlines()
    lines = [clean_text(l) for l in lines]
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if s.startswith("|"):
            rows, i = parse_table(lines, i)
            if rows:
                add_table(doc, rows)
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            add_heading(doc, len(m.group(1)), m.group(2)); i += 1; continue
        if s == "---":
            i += 1; continue  # sem divisores entre seções
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip()); i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            add_runs(p, " ".join(b for b in buf if b))
            for r in p.runs:
                r.italic = True
            continue
        mnum = re.match(r"^(\d+)\.\s+(.*)$", s)
        if mnum:
            parts = [mnum.group(2)]
            j = i + 1
            while j < len(lines) and not is_special(lines[j]):
                parts.append(lines[j].strip()); j += 1
            p = doc.add_paragraph(style="List Number")
            add_runs(p, " ".join(parts)); style_runs(p)
            i = j; continue
        if s.startswith("- ") or s.startswith("* "):
            parts = [s[2:]]
            j = i + 1
            while j < len(lines) and not is_special(lines[j]):
                parts.append(lines[j].strip()); j += 1
            p = doc.add_paragraph(style="List Bullet")
            add_runs(p, " ".join(parts)); style_runs(p)
            i = j; continue
        text, i = gather_continuation(lines, i)
        p = doc.add_paragraph()
        add_runs(p, text)


def main():
    import sys
    with_appendix = "--apendice" in sys.argv

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    normal.font.color.rgb = BLACK
    # garante Arial também para east-asian/complex
    rpr = normal.element.get_or_add_rPr().get_or_add_rFonts()
    rpr.set(qn("w:ascii"), FONT); rpr.set(qn("w:hAnsi"), FONT); rpr.set(qn("w:cs"), FONT)

    render_md(doc, ANALYSIS)
    if with_appendix:
        add_hr(doc)
        render_md(doc, DATASET, page_break_before=True)

    doc.save(OUT)
    print(f"Gerado: {OUT} ({'com' if with_appendix else 'sem'} apêndice)")


if __name__ == "__main__":
    main()
