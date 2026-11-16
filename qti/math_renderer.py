import html
import re


MATH_MARKER_PATTERN = re.compile(
    r"\{\{(MATH\s+\d+)\}\}"
)


def build_math_lookup(question):
    """
    Build a lookup of CourseCraft math objects.

    Example:

        {
            "MATH 1": {
                "id": "MATH 1",
                "latex": "...",
                "location": "prompt"
            }
        }
    """

    lookup = {}

    for math_item in question.get("math", []) or []:

        if not isinstance(math_item, dict):
            continue

        math_id = math_item.get("id")

        if not math_id:
            continue

        lookup[str(math_id).strip()] = math_item

    return lookup


def normalize_latex(latex):
    """
    Perform very small LaTeX cleanup without changing
    the mathematical meaning.
    """

    if latex is None:
        return ""

    latex = str(latex).strip()

    # Common function normalization.
    replacements = {
        r"\frac{sin(": r"\frac{\sin(",
        r"\frac{cos(": r"\frac{\cos(",
        r"\frac{tan(": r"\frac{\tan(",
    }

    for old, new in replacements.items():
        latex = latex.replace(old, new)

    return latex


def latex_to_canvas_html(latex):
    """
    Convert CourseCraft LaTeX into HTML that can be
    embedded inside Canvas QTI question content.

    Canvas can preserve TeX source in an element for
    mathematical rendering. The LaTeX is HTML-escaped
    so XML/HTML special characters cannot corrupt QTI.

    We retain the original LaTeX expression rather than
    converting it back into flattened plain text.
    """

    latex = normalize_latex(latex)

    if not latex:
        return ""

    escaped = html.escape(
        latex,
        quote=True,
    )

    return (
        '<span class="math-tex">'
        "\\("
        f"{escaped}"
        "\\)"
        "</span>"
    )


def plain_text_to_html(text):
    """
    Escape ordinary question text and preserve line
    breaks for Canvas HTML.
    """

    if text is None:
        return ""

    escaped = html.escape(
        str(text),
        quote=False,
    )

    return escaped.replace(
        "\n",
        "<br/>",
    )


def render_math_marker(math_id, math_lookup):
    """
    Resolve one {{MATH N}} marker.

    Returns None when the marker cannot be resolved.
    This lets validation detect broken references rather
    than silently deleting them.
    """

    math_item = math_lookup.get(
        math_id
    )

    if not math_item:
        return None

    latex = math_item.get(
        "latex"
    )

    if not latex:
        return None

    return latex_to_canvas_html(
        latex
    )


def render_text_with_math(
    text,
    question,
):
    """
    Convert CourseCraft text containing math markers
    into Canvas-ready HTML.

    Example input:

        Evaluate:

        {{MATH 2}}

    becomes ordinary escaped HTML followed by the
    rendered mathematical expression.
    """

    if text is None:
        return ""

    text = str(text)

    math_lookup = build_math_lookup(
        question
    )

    parts = MATH_MARKER_PATTERN.split(
        text
    )

    output = []

    for index, part in enumerate(parts):

        if not part:
            continue

        # re.split() places the captured MATH ID at
        # every odd position.
        is_math_id = (
            index % 2 == 1
        )

        if is_math_id:

            rendered = render_math_marker(
                part,
                math_lookup,
            )

            if rendered is None:
                # Keep the marker visible instead of
                # silently losing mathematical content.
                output.append(
                    plain_text_to_html(
                        "{{"
                        + part
                        + "}}"
                    )
                )

            else:
                output.append(
                    rendered
                )

        else:
            output.append(
                plain_text_to_html(
                    part
                )
            )

    return "".join(output)


def render_prompt(question):
    """
    Render a question prompt for QTI export.
    """

    return render_text_with_math(
        question.get(
            "prompt",
            ""
        ),
        question,
    )


def render_feedback(question):
    """
    Render general feedback.

    This already supports {{MATH N}} markers if the AI
    associates math with feedback.
    """

    return render_text_with_math(
        question.get(
            "feedback",
            ""
        ),
        question,
    )


def render_choice(
    choice,
    question,
):
    """
    Render an answer choice.

    Supports both:

        choice["text"] = "..."
        choice["math"] = [...]

    If choice-level math exists, it is temporarily merged
    with question-level math for marker resolution.
    """

    choice_text = choice.get(
        "text",
        ""
    )

    choice_math = choice.get(
        "math",
        [],
    ) or []

    if not choice_math:
        return render_text_with_math(
            choice_text,
            question,
        )

    combined_question = dict(
        question
    )

    combined_math = list(
        question.get(
            "math",
            [],
        ) or []
    )

    combined_math.extend(
        choice_math
    )

    combined_question[
        "math"
    ] = combined_math

    return render_text_with_math(
        choice_text,
        combined_question,
    )


def find_math_markers(text):
    """
    Return every CourseCraft math marker referenced
    inside a string.
    """

    if not text:
        return []

    return MATH_MARKER_PATTERN.findall(
        str(text)
    )


def unresolved_math_markers(
    text,
    question,
):
    """
    Return math markers that cannot be resolved from
    the question's math data.
    """

    lookup = build_math_lookup(
        question
    )

    unresolved = []

    for math_id in find_math_markers(
        text
    ):

        math_item = lookup.get(
            math_id
        )

        if (
            not math_item
            or not math_item.get("latex")
        ):
            unresolved.append(
                math_id
            )

    return unresolved


def validate_question_math(question):
    """
    Validate CourseCraft math references before QTI
    generation.

    Returns a list of human-readable problems.
    """

    problems = []

    math_items = question.get(
        "math",
        [],
    ) or []

    # ---------------------------------------------
    # Validate math objects
    # ---------------------------------------------

    seen_ids = set()

    for math_item in math_items:

        if not isinstance(
            math_item,
            dict,
        ):
            problems.append(
                "Math entry is not a valid object."
            )
            continue

        math_id = math_item.get(
            "id"
        )

        latex = math_item.get(
            "latex"
        )

        if not math_id:
            problems.append(
                "Math entry is missing an id."
            )
            continue

        if math_id in seen_ids:
            problems.append(
                f"Duplicate math id: {math_id}"
            )

        seen_ids.add(
            math_id
        )

        if not latex:
            problems.append(
                f"{math_id} is missing LaTeX."
            )

    # ---------------------------------------------
    # Validate prompt references
    # ---------------------------------------------

    for math_id in unresolved_math_markers(
        question.get(
            "prompt",
            ""
        ),
        question,
    ):
        problems.append(
            f"Prompt contains unresolved "
            f"math marker: {math_id}"
        )

    # ---------------------------------------------
    # Validate feedback references
    # ---------------------------------------------

    for math_id in unresolved_math_markers(
        question.get(
            "feedback",
            ""
        ),
        question,
    ):
        problems.append(
            f"Feedback contains unresolved "
            f"math marker: {math_id}"
        )

    # ---------------------------------------------
    # Validate choices
    # ---------------------------------------------

    for choice_index, choice in enumerate(
        question.get(
            "choices",
            [],
        ) or [],
        start=1,
    ):

        combined_question = dict(
            question
        )

        combined_math = list(
            question.get(
                "math",
                [],
            ) or []
        )

        combined_math.extend(
            choice.get(
                "math",
                [],
            ) or []
        )

        combined_question[
            "math"
        ] = combined_math

        unresolved = (
            unresolved_math_markers(
                choice.get(
                    "text",
                    ""
                ),
                combined_question,
            )
        )

        for math_id in unresolved:

            problems.append(
                f"Choice {choice_index} contains "
                f"unresolved math marker: {math_id}"
            )

    return problems


def has_math(question):
    """
    Return True when a question contains CourseCraft
    structured mathematical content.
    """

    return bool(
        question.get(
            "math",
            []
        )
    )