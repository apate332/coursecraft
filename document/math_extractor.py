from lxml import etree
from document.math_converter import omml_to_latex


MATH_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/math"
)

MATH_TEXT_TAG = f"{{{MATH_NS}}}t"


def contains_math(paragraph):
    """
    Return True when a Word paragraph contains
    an Office Math / OMML equation.
    """

    return bool(
        paragraph._element.xpath(
            ".//m:oMath | .//m:oMathPara"
        )
    )


def get_math_nodes(paragraph):
    """
    Return each actual OMML equation in a paragraph.

    We return oMath only, rather than both oMath and
    oMathPara, to avoid duplicate equations.
    """

    return paragraph._element.xpath(
        ".//m:oMath"
    )


def omml_text(math_element):
    """
    Extract visible text tokens from an OMML equation.

    We intentionally avoid namespace-prefixed XPath here
    because math_element is a plain lxml element and its
    XPath evaluator may not know the 'm' prefix.

    This text is only a fallback/debug representation.
    The original OMML XML is retained for structural
    conversion later.
    """

    tokens = []

    for element in math_element.iter():

        if element.tag == MATH_TEXT_TAG:
            if element.text:
                tokens.append(
                    element.text
                )

    return "".join(tokens).strip()


def extract_math_from_paragraph(paragraph):
    """
    Extract all Word equations from a paragraph.

    Each equation retains:
      - fallback visible text
      - original OMML XML

    The XML will later allow CourseCraft to preserve
    fractions, radicals, scripts, integrals, matrices,
    limits, and other complex mathematical structures.
    """

    equations = []

    for math_element in get_math_nodes(
        paragraph
    ):

        equations.append(
            {
               "format": "latex",
                "text": omml_text(
                    math_element
                ),
                "latex": omml_to_latex(
                    math_element
                ),
                "xml": etree.tostring(
                    math_element,
                    encoding="unicode",
                ),
             }
        )

    return equations