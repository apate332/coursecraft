from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def extract_docx(file_path):
    document = Document(file_path)

    content = []
    table_number = 0

    for block in document.iter_inner_content():

        if isinstance(block, Paragraph):
            text = block.text.strip()

            if text:
                content.append(text)

        elif isinstance(block, Table):
            table_number += 1

            content.append(f"\n[TABLE {table_number}]")

            for row in block.rows:
                cells = []

                for cell in row.cells:
                    text = cell.text.strip()
                    cells.append(text)

                content.append(" | ".join(cells))

            content.append("[END TABLE]\n")

    return "\n".join(content)