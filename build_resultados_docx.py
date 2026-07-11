"""
Gera um .docx no mesmo padrão visual do validacao_qualitativa.docx (Arial 12, preto,
tabelas do Word, sem emoji) a partir de um markdown em docs/. Reutiliza a maquinaria de
build_qualitative_docx.py.

Uso:
    python build_resultados_docx.py                       # default: resultados_discussao
    python build_resultados_docx.py docs/outra_secao.md   # qualquer markdown
"""
import sys

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

from build_qualitative_docx import render_md, FONT, BODY_PT, BLACK

SOURCE = "docs/resultados_discussao.md"


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE
    out = source.rsplit(".", 1)[0] + ".docx"
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    normal.font.color.rgb = BLACK
    rpr = normal.element.get_or_add_rPr().get_or_add_rFonts()
    rpr.set(qn("w:ascii"), FONT)
    rpr.set(qn("w:hAnsi"), FONT)
    rpr.set(qn("w:cs"), FONT)

    render_md(doc, source)

    doc.save(out)
    print(f"Gerado: {out}")


if __name__ == "__main__":
    main()
