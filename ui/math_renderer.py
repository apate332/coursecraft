import re

import streamlit as st


MATH_MARKER_PATTERN = re.compile(
    r"\{\{(MATH\s+\d+)\}\}"
)


def get_math_lookup(question):
    """
    Build a lookup such as:

        {
            "MATH 1": {
                "id": "MATH 1",
                "latex": "...",
                "location": "prompt"
            }
        }
    """

    lookup = {}

    for math_item in question.get(
        "math",
        [],
    ):
        math_id = math_item.get("id")

        if math_id:
            lookup[math_id] = math_item

    return lookup


def render_latex(latex):
    """
    Render a LaTeX expression safely.

    Falls back to code display if Streamlit cannot
    render the supplied expression.
    """

    if not latex:
        return

    try:
        st.latex(latex)

    except Exception:
        st.code(
            latex,
            language=None,
        )


def render_math_aware_text(
    text,
    question,
):
    """
    Render text containing CourseCraft math markers.

    Example:

        Evaluate:

        {{MATH 2}}

    becomes:

        Evaluate:

        [rendered LaTeX equation]
    """

    if not text:
        return

    math_lookup = get_math_lookup(
        question
    )

    parts = MATH_MARKER_PATTERN.split(
        str(text)
    )

    for part in parts:

        if not part:
            continue

        # -----------------------------------------
        # MATH MARKER
        # -----------------------------------------

        if part in math_lookup:

            math_item = math_lookup[
                part
            ]

            latex = math_item.get(
                "latex"
            )

            if latex:
                render_latex(
                    latex
                )

            else:
                st.caption(
                    f"{part} could not be rendered."
                )

        # -----------------------------------------
        # NORMAL TEXT
        # -----------------------------------------

        else:

            cleaned = part.strip()

            if cleaned:
                st.markdown(
                    cleaned
                )


def render_question_math(question):
    """
    Render math associated with a question that
    does not already appear through a {{MATH N}}
    marker in the prompt.

    Prevents an equation from silently disappearing
    if the AI preserved the math object but omitted
    the marker.
    """

    prompt = str(
        question.get(
            "prompt",
            "",
        )
    )

    for math_item in question.get(
        "math",
        [],
    ):

        math_id = math_item.get(
            "id"
        )

        latex = math_item.get(
            "latex"
        )

        location = math_item.get(
            "location"
        )

        if not latex:
            continue

        marker = (
            "{{"
            + str(math_id)
            + "}}"
        )

        if marker in prompt:
            continue

        if location in {
            "prompt",
            "stimulus",
            "other",
        }:
            render_latex(
                latex
            )


def render_question_preview(question):
    """
    Render the student-facing question prompt with
    mathematical expressions in their intended places.
    """

    render_math_aware_text(
        question.get(
            "prompt",
            "",
        ),
        question,
    )

    render_question_math(
        question
    )