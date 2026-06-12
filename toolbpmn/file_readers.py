"""Parsers para los distintos formatos de entrada de documentos."""

import io
from pathlib import Path


def read_txt(file) -> str:
    """Lee archivo .txt o .md (objeto UploadedFile de Streamlit o path)."""
    if hasattr(file, "read"):
        raw = file.read()
        return raw.decode("utf-8", errors="replace")
    return Path(file).read_text(encoding="utf-8", errors="replace")


def read_docx(file) -> str:
    """Extrae texto plano de un .docx preservando orden de párrafos y tablas."""
    from docx import Document

    if hasattr(file, "read"):
        doc = Document(io.BytesIO(file.read()))
    else:
        doc = Document(file)

    parts = []
    for block in _iter_blocks(doc):
        text = block.strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _iter_blocks(doc):
    """Itera párrafos y celdas de tabla en orden de aparición."""
    from docx.oxml.ns import qn

    body = doc.element.body
    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            yield child.text_content() if hasattr(child, "text_content") else "".join(
                n.text or "" for n in child.iter() if hasattr(n, "text") and n.text
            )
        elif tag == "tbl":
            for row in child.iter(qn("w:tr")):
                cells = []
                for cell in row.iter(qn("w:tc")):
                    cells.append(
                        "".join(
                            n.text or ""
                            for n in cell.iter()
                            if hasattr(n, "text") and n.text
                        ).strip()
                    )
                yield " | ".join(cells)


def read_xlsx(file) -> str:
    """Extrae texto de todas las hojas de un .xlsx como texto tabular."""
    import openpyxl

    if hasattr(file, "read"):
        wb = openpyxl.load_workbook(io.BytesIO(file.read()), data_only=True)
    else:
        wb = openpyxl.load_workbook(file, data_only=True)

    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"=== Hoja: {sheet_name} ===")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            line = " | ".join(cells).strip(" |")
            if line.replace("|", "").strip():
                parts.append(line)
    return "\n".join(parts)


def extract_text(file, filename: str) -> str:
    """Despacha al parser correcto según extensión."""
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md"):
        return read_txt(file)
    if ext == ".docx":
        return read_docx(file)
    if ext in (".xlsx", ".xls"):
        return read_xlsx(file)
    raise ValueError(f"Formato no soportado: {ext}")
