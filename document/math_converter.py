from lxml import etree


MATH_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/math"
)

M = f"{{{MATH_NS}}}"


# =========================================================
# HELPERS
# =========================================================

def local_name(element):
    """
    Return an XML element's local tag name.

    Example:
        {namespace}f -> f
    """

    return etree.QName(
        element
    ).localname


def children(element):
    """
    Return element children only.
    """

    return [
        child
        for child in element
        if isinstance(
            child.tag,
            str,
        )
    ]


def first_child(element, name):
    """
    Find the first direct child with a given
    OMML local name.
    """

    for child in children(element):
        if local_name(child) == name:
            return child

    return None


def text_content(element):
    """
    Collect visible OMML text from an element.
    """

    values = []

    for node in element.iter():

        if (
            isinstance(node.tag, str)
            and local_name(node) == "t"
            and node.text
        ):
            values.append(
                node.text
            )

    return "".join(values)


# =========================================================
# SYMBOL NORMALIZATION
# =========================================================

def normalize_text(value):
    """
    Convert common mathematical Unicode symbols
    into LaTeX equivalents.
    """

    if not value:
        return ""

    replacements = {
        "±": r"\pm ",
        "×": r"\times ",
        "÷": r"\div ",
        "≤": r"\le ",
        "≥": r"\ge ",
        "≠": r"\ne ",
        "≈": r"\approx ",
        "∞": r"\infty ",
        "→": r"\to ",
        "←": r"\leftarrow ",
        "∂": r"\partial ",
        "∇": r"\nabla ",
        "α": r"\alpha ",
        "β": r"\beta ",
        "γ": r"\gamma ",
        "δ": r"\delta ",
        "θ": r"\theta ",
        "λ": r"\lambda ",
        "μ": r"\mu ",
        "π": r"\pi ",
        "σ": r"\sigma ",
        "Σ": r"\Sigma ",
        "Δ": r"\Delta ",
    }

    for source, replacement in replacements.items():
        value = value.replace(
            source,
            replacement,
        )

    return value


# =========================================================
# CONTAINER CONVERSION
# =========================================================

def convert_children(element):
    return "".join(
        convert_node(child)
        for child in children(element)
    )


def convert_container(element):
    """
    Convert a structural OMML container such as:
        numerator
        denominator
        base
        superscript
        subscript
        degree
    """

    if element is None:
        return ""

    return convert_children(
        element
    )


# =========================================================
# FRACTION
# =========================================================

def convert_fraction(element):
    """
    OMML:

        m:f
            m:num
            m:den

    LaTeX:

        \\frac{numerator}{denominator}
    """

    numerator = first_child(
        element,
        "num",
    )

    denominator = first_child(
        element,
        "den",
    )

    numerator_latex = convert_container(
        numerator
    )

    denominator_latex = convert_container(
        denominator
    )

    return (
        r"\frac{"
        + numerator_latex
        + "}{"
        + denominator_latex
        + "}"
    )


# =========================================================
# RADICAL
# =========================================================

def convert_radical(element):
    """
    Handles:

        sqrt(x)

    and:

        nth-root(x)
    """

    degree = first_child(
        element,
        "deg",
    )

    base = first_child(
        element,
        "e",
    )

    base_latex = convert_container(
        base
    )

    degree_latex = convert_container(
        degree
    )

    if not degree_latex:
        return (
            r"\sqrt{"
            + base_latex
            + "}"
        )

    return (
        r"\sqrt["
        + degree_latex
        + "]{"
        + base_latex
        + "}"
    )


# =========================================================
# SUPERSCRIPT
# =========================================================

def convert_superscript(element):
    """
    OMML:
        x with superscript 2

    LaTeX:
        x^{2}
    """

    base = first_child(
        element,
        "e",
    )

    superscript = first_child(
        element,
        "sup",
    )

    return (
        convert_container(base)
        + "^{"
        + convert_container(
            superscript
        )
        + "}"
    )


# =========================================================
# SUBSCRIPT
# =========================================================

def convert_subscript(element):
    """
    OMML:
        x with subscript i

    LaTeX:
        x_{i}
    """

    base = first_child(
        element,
        "e",
    )

    subscript = first_child(
        element,
        "sub",
    )

    return (
        convert_container(base)
        + "_{"
        + convert_container(
            subscript
        )
        + "}"
    )


# =========================================================
# SUBSCRIPT + SUPERSCRIPT
# =========================================================

def convert_sub_sup(element):
    """
    OMML:
        x_i^2

    LaTeX:
        x_{i}^{2}
    """

    base = first_child(
        element,
        "e",
    )

    subscript = first_child(
        element,
        "sub",
    )

    superscript = first_child(
        element,
        "sup",
    )

    return (
        convert_container(base)
        + "_{"
        + convert_container(
            subscript
        )
        + "}^{"
        + convert_container(
            superscript
        )
        + "}"
    )


# =========================================================
# DELIMITERS
# =========================================================

def convert_delimiter(element):
    """
    Preserve grouped mathematical expressions.

    For now we use parentheses.

    Later we can inspect OMML delimiter properties
    to preserve brackets, braces, absolute value, etc.
    """

    expressions = []

    for child in children(element):

        if local_name(child) == "e":
            expressions.append(
                convert_container(
                    child
                )
            )

    return (
        r"\left("
        + ",".join(expressions)
        + r"\right)"
    )


# =========================================================
# FUNCTION
# =========================================================

def convert_function(element):
    """
    Handles Word function structures.

    Example:
        sin(x)
        cos(x)
        log(x)
    """

    function_name = first_child(
        element,
        "fName",
    )

    expression = first_child(
        element,
        "e",
    )

    name = convert_container(
        function_name
    ).strip()

    expression_latex = convert_container(
        expression
    )

    known_functions = {
        "sin",
        "cos",
        "tan",
        "log",
        "ln",
        "exp",
    }

    if name in known_functions:
        name = "\\" + name

    return (
        name
        + r"\left("
        + expression_latex
        + r"\right)"
    )

# =========================================================
# COMBINED SUBSCRIPT + SUPERSCRIPT
# =========================================================

def convert_sub_sup(element):
    """
    Convert structures such as:

        x_i^2

    into:

        x_{i}^{2}
    """

    base = first_child(element, "e")
    subscript = first_child(element, "sub")
    superscript = first_child(element, "sup")

    return (
        convert_container(base)
        + "_{"
        + convert_container(subscript)
        + "}^{"
        + convert_container(superscript)
        + "}"
    )


# =========================================================
# N-ARY OPERATORS
# =========================================================

def get_property_value(element, property_name):
    """
    Read the m:val value from an OMML property.

    Used for structures such as integrals,
    summations, and products.
    """

    if element is None:
        return None

    for node in element.iter():

        if (
            isinstance(node.tag, str)
            and local_name(node) == property_name
        ):
            for key, value in node.attrib.items():

                if key.endswith("}val") or key == "val":
                    return value

    return None


def convert_nary(element):
    """
    Convert OMML n-ary structures.

    Examples:

        integral
        summation
        product

    OMML typically stores:

        naryPr
        sub
        sup
        e
    """

    properties = first_child(
        element,
        "naryPr",
    )

    subscript = first_child(
        element,
        "sub",
    )

    superscript = first_child(
        element,
        "sup",
    )

    expression = first_child(
        element,
        "e",
    )

    character = get_property_value(
        properties,
        "chr",
    )

    operators = {
        "∫": r"\int",
        "∑": r"\sum",
        "Σ": r"\sum",
        "∏": r"\prod",
        "∐": r"\coprod",
        "⋃": r"\bigcup",
        "⋂": r"\bigcap",
    }

    operator = operators.get(
        character,
        normalize_text(character or ""),
    )

    result = operator

    sub_latex = convert_container(
        subscript
    )

    sup_latex = convert_container(
        superscript
    )

    if sub_latex:
        result += "_{" + sub_latex + "}"

    if sup_latex:
        result += "^{" + sup_latex + "}"

    expression_latex = convert_container(
        expression
    )

    if expression_latex:
        result += " " + expression_latex

    return result


# =========================================================
# LIMITS
# =========================================================

def convert_limit_lower(element):
    """
    Convert a lower-limit structure.

    Common example:

        lim_(x -> 0)
    """

    base = first_child(
        element,
        "e",
    )

    limit = first_child(
        element,
        "lim",
    )

    base_latex = convert_container(
        base
    ).strip()

    limit_latex = convert_container(
        limit
    )

    if base_latex == "lim":
        base_latex = r"\lim"

    return (
        base_latex
        + "_{"
        + limit_latex
        + "}"
    )


def convert_limit_upper(element):
    """
    Convert an upper-limit OMML structure.
    """

    base = first_child(
        element,
        "e",
    )

    limit = first_child(
        element,
        "lim",
    )

    return (
        convert_container(base)
        + "^{"
        + convert_container(limit)
        + "}"
    )


# =========================================================
# MATRICES
# =========================================================

def convert_matrix(element):
    """
    Convert an OMML matrix into LaTeX.

    Example:

        1  2
        3  4

    becomes:

        \\begin{matrix}
        1 & 2 \\\\
        3 & 4
        \\end{matrix}
    """

    rows = []

    for row in children(element):

        if local_name(row) != "mr":
            continue

        cells = []

        for cell in children(row):

            if local_name(cell) == "e":
                cells.append(
                    convert_container(cell)
                )

        rows.append(
            " & ".join(cells)
        )

    body = r" \\ ".join(rows)

    return (
        r"\begin{matrix}"
        + body
        + r"\end{matrix}"
    )


# =========================================================
# EQUATION ARRAYS
# =========================================================

def convert_equation_array(element):
    """
    Convert multiple aligned equations.

    Example:

        x + y = 5
        2x - y = 1
    """

    rows = []

    for child in children(element):

        if local_name(child) == "e":
            rows.append(
                convert_container(child)
            )

    body = r" \\ ".join(rows)

    return (
        r"\begin{aligned}"
        + body
        + r"\end{aligned}"
    )


# =========================================================
# NODE DISPATCH
# =========================================================

def convert_node(element):
    """
    Recursively convert one OMML node into LaTeX.
    """

    if element is None:
        return ""

    name = local_name(
        element
    )

    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    if name == "t":
        return normalize_text(
            element.text or ""
        )

    # -----------------------------------------------------
    # RUN
    # -----------------------------------------------------

    if name == "r":
        return convert_children(
            element
        )

    # -----------------------------------------------------
    # EQUATION / CONTAINERS
    # -----------------------------------------------------

    if name in {
        "oMath",
        "oMathPara",
        "e",
        "num",
        "den",
        "sup",
        "sub",
        "deg",
        "fName",
    }:
        return convert_children(
            element
        )

    # -----------------------------------------------------
    # STRUCTURED MATH
    # -----------------------------------------------------

    if name == "f":
        return convert_fraction(
            element
        )

    if name == "rad":
        return convert_radical(
            element
        )

    if name == "sSup":
        return convert_superscript(
            element
        )

    if name == "sSub":
        return convert_subscript(
            element
        )

    if name == "sSubSup":
        return convert_sub_sup(
            element
        )

    if name == "d":
        return convert_delimiter(
            element
        )

    if name == "func":
        return convert_function(
            element
        )

    if name == "nary":
        return convert_nary(
            element
        )

    if name == "limLow":
        return convert_limit_lower(
            element
        )

    if name == "limUpp":
        return convert_limit_upper(
            element
        )

    if name == "m":
        return convert_matrix(
            element
        )

    if name == "eqArr":
        return convert_equation_array(
            element
        )
    
    # -----------------------------------------------------
    # PROPERTY NODES
    # -----------------------------------------------------

    if name.endswith("Pr"):
        return ""

    # -----------------------------------------------------
    # UNKNOWN STRUCTURE
    # -----------------------------------------------------

    # Don't throw away unknown OMML structures.
    # Recursively process their children so CourseCraft
    # preserves as much content as possible.
    return convert_children(
        element
    )


# =========================================================
# PUBLIC API
# =========================================================

def omml_to_latex(math_element):
    """
    Convert one OMML equation element into LaTeX.

    Current structural support:

        text
        fractions
        radicals
        superscripts
        subscripts
        subscript + superscript
        delimiters
        common functions

    Upcoming:

        integrals
        summations/products
        limits
        matrices
        accents
        equation arrays
    """

    latex = convert_node(
        math_element
    )

    # Clean repeated whitespace without destroying
    # LaTeX commands.
    latex = " ".join(
        latex.split()
    )

    return latex.strip()