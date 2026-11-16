from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from document.math_extractor import (
    contains_math,
    extract_math_from_paragraph,
)


def extract_docx(file_path):
    """
    Extract ordered curriculum content from a DOCX.

    Preserves:
    - ordinary paragraphs
    - Word equation objects
    - tables

    Equations are marked explicitly so the AI can
    distinguish mathematical content from normal prose.
    """

    document = Document(file_path)

    content = []
    table_number = 0
    equation_number = 0

    for block in document.iter_inner_content():

        # =================================================
        # PARAGRAPHS
        # =================================================

        if isinstance(block, Paragraph):

            text = block.text.strip()

            # Preserve ordinary paragraph text.
            if text:
                content.append(text)

            # Preserve Word Equation Editor objects.
            if contains_math(block):

                equations = (
                    extract_math_from_paragraph(
                        block
                    )
                )

                for equation in equations:

                    equation_number += 1

                    content.append(
                        f"\n[MATH {equation_number}]"
                    )

                    content.append(
                        "[LATEX]"
                    )

                    content.append(
                     equation.get(
                        "latex",
                       equation["text"],
                         )
                    )
                    content.append(
                        "[/LATEX]"
                    )

                    content.append(
                        f"[END MATH {equation_number}]\n"
                    )

        # =================================================
        # TABLES
        # =================================================

        elif isinstance(block, Table):

            table_number += 1

            content.append(
                f"\n[TABLE {table_number}]"
            )

            for row in block.rows:

                cells = []

                for cell in row.cells:

                    text = (
                        cell.text.strip()
                    )

                    cells.append(
                        text
                    )

                content.append(
                    " | ".join(cells)
                )

            content.append(
                "[END TABLE]\n"
            )

    return "\n".join(content)