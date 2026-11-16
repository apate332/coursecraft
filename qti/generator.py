import hashlib
import html
import uuid

from qti.math_renderer import (
    render_prompt,
    render_choice,
    render_feedback,
    validate_question_math,
)
# =========================================================
# CANVAS / QTI CONSTANTS
# =========================================================

QTI_NAMESPACE = (
    'xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="'
    'http://www.imsglobal.org/xsd/ims_qtiasiv1p2 '
    'http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd"'
)


CANVAS_TYPES = {
    "multiple_choice": "multiple_choice_question",
    "multiple_answer": "multiple_answers_question",
    "numeric": "numerical_question",
}


# =========================================================
# BASIC HELPERS
# =========================================================

def xml_escape(value):
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def clean_number(value):
    """
    Avoid unnecessary float noise.

    87.0 -> 87
    1.0  -> 1
    """

    if value is None:
        return "0"

    number = float(value)

    if number.is_integer():
        return str(int(number))

    return format(
        number,
        ".12g",
    )


def random_ident():
    """
    Canvas-style unique package/item identifier.
    """

    return "g" + uuid.uuid4().hex


def hash_ident(value):
    """
    Stable Canvas-style identifier derived from input.
    """

    digest = hashlib.md5(
        str(value).encode("utf-8")
    ).hexdigest()

    return "g" + digest


def get_points(question):
    if question.get("zero_point"):
        return 0

    points = question.get("points")

    if points is None:
        return 1

    return points


def get_feedback(question):
    """
    Normalize CourseCraft feedback.

    Existing ASU AI output may contain either:
      "feedback": "text"

    or eventually:
      "feedback": {
          "general": "...",
          "correct": "...",
          "incorrect": "..."
      }
    """

    feedback = question.get("feedback")

    result = {
        "general": "",
        "correct": "",
        "incorrect": "",
    }

    if not feedback:
        return result

    if isinstance(feedback, str):
        result["general"] = feedback
        return result

    if isinstance(feedback, dict):
        result["general"] = (
            feedback.get("general")
            or ""
        )

        result["correct"] = (
            feedback.get("correct")
            or ""
        )

        result["incorrect"] = (
            feedback.get("incorrect")
            or ""
        )

    return result


# =========================================================
# XML HELPERS
# =========================================================

def meta_field(label, entry):
    label = xml_escape(label)

    if entry is None or entry == "":
        return f"""<qtimetadatafield>
  <fieldlabel>{label}</fieldlabel>
  <fieldentry/>
</qtimetadatafield>"""

    return f"""<qtimetadatafield>
  <fieldlabel>{label}</fieldlabel>
  <fieldentry>{xml_escape(entry)}</fieldentry>
</qtimetadatafield>"""


def score_condition(condition_xml):
    return f"""<respcondition continue="No">
  <conditionvar>
    {condition_xml}
  </conditionvar>
  <setvar action="Set" varname="SCORE">100</setvar>
</respcondition>"""


def resprocessing(conditions):
    decvar = (
        '<outcomes>'
        '<decvar maxvalue="100" minvalue="0" '
        'varname="SCORE" vartype="Decimal"/>'
        '</outcomes>'
    )

    parts = [
        decvar,
        *conditions,
    ]

    return (
        "<resprocessing>\n"
        + "\n".join(parts)
        + "\n</resprocessing>"
    )


def feedback_xml(identifier, text):
    if not text:
        return ""

    return f"""<itemfeedback ident="{identifier}">
  <flow_mat>
    <material>
      <mattext texttype="text/html">{xml_escape(text)}</mattext>
    </material>
  </flow_mat>
</itemfeedback>"""


# =========================================================
# NUMERIC RULES
# =========================================================

def numeric_rule(question):
    """
    Convert CourseCraft numeric fields into the same
    conceptual model used by the working reference exporter.

    Example:
        answer = 87
        tolerance = 1

    becomes:
        exact = 87
        margin = 1
        low = 86
        high = 88
    """

    answer = question.get(
        "numeric_answer"
    )

    tolerance = question.get(
        "numeric_tolerance"
    )

    numeric_min = question.get(
        "numeric_min"
    )

    numeric_max = question.get(
        "numeric_max"
    )

    # Standard CourseCraft numeric answer.
    if answer is not None:

        exact = float(answer)

        margin = abs(
            float(
                tolerance
                if tolerance is not None
                else 0
            )
        )

        return {
            "kind": "exact",
            "exact": exact,
            "margin": margin,
            "low": exact - margin,
            "high": exact + margin,
        }

    # Optional future range support.
    if (
        numeric_min is not None
        and numeric_max is not None
    ):

        return {
            "kind": "range",
            "low": float(numeric_min),
            "high": float(numeric_max),
        }

    raise ValueError(
        "Numeric question is missing an answer."
    )


# =========================================================
# CHOICE QUESTIONS
# =========================================================

def choice_question_xml(
    question,
    item_ident,
    answer_base,
):
    question_type = question["type"]

    multiple = (
        question_type
        == "multiple_answer"
    )

    choices = question.get(
        "choices",
        [],
    )

    if not choices:
        raise ValueError(
            f"Question {question.get('number')} "
            "has no answer choices."
        )

    response_labels = []

    correct_answer_ids = []
    incorrect_answer_ids = []

    all_answer_ids = []

    for index, choice in enumerate(
        choices
    ):

        answer_id = str(
            answer_base + index + 1
        )

        all_answer_ids.append(
            answer_id
        )

        # Math-aware Canvas HTML.
        choice_html = render_choice(
            choice,
            question,
        )

        response_labels.append(
            f"""<response_label ident="{answer_id}">
  <material>
    <mattext texttype="text/html"><![CDATA[{choice_html}]]></mattext>
  </material>
</response_label>"""
        )

        if choice.get("correct"):
            correct_answer_ids.append(
                answer_id
            )
        else:
            incorrect_answer_ids.append(
                answer_id
            )

    if question_type == "multiple_choice":

        if len(correct_answer_ids) != 1:
            raise ValueError(
                f"Question {question.get('number')} "
                "must have exactly one correct answer."
            )

        condition = (
            '<varequal respident="response1">'
            f'{correct_answer_ids[0]}'
            '</varequal>'
        )

    else:

        if not correct_answer_ids:
            raise ValueError(
                f"Question {question.get('number')} "
                "must have at least one correct answer."
            )

        pieces = []

        for answer_id in correct_answer_ids:
            pieces.append(
                '<varequal respident="response1">'
                f'{answer_id}'
                '</varequal>'
            )

        for answer_id in incorrect_answer_ids:
            pieces.append(
                "<not>"
                '<varequal respident="response1">'
                f'{answer_id}'
                '</varequal>'
                "</not>"
            )

        condition = (
            "<and>\n"
            + "\n".join(pieces)
            + "\n</and>"
        )

    presentation_extra = f"""<response_lid
    ident="response1"
    rcardinality="{'Multiple' if multiple else 'Single'}">
  <render_choice>
    {"".join(response_labels)}
  </render_choice>
</response_lid>"""

    processing = resprocessing(
        [
            score_condition(
                condition
            )
        ]
    )

    return (
        presentation_extra,
        processing,
        ",".join(all_answer_ids),
    )


# =========================================================
# NUMERIC QUESTION
# =========================================================

def numeric_question_xml(question):
    """
    Canvas-compatible numeric response based directly on
    the working reference implementation.

    Important difference from our old exporter:

    <varequal> contains:
        margintype="absolute"
        margin="..."

    AND Canvas receives the equivalent low/high range.
    """

    rule = numeric_rule(
        question
    )

    presentation_extra = """<response_str
    ident="response1"
    rcardinality="Single">
  <render_fib fibtype="Decimal">
    <response_label ident="answer1"/>
  </render_fib>
</response_str>"""

    if rule["kind"] == "exact":

        condition = f"""<or>
  <varequal
      respident="response1"
      margintype="absolute"
      margin="{clean_number(rule["margin"])}">{clean_number(rule["exact"])}</varequal>
  <and>
    <vargte respident="response1">{clean_number(rule["low"])}</vargte>
    <varlte respident="response1">{clean_number(rule["high"])}</varlte>
  </and>
</or>"""

    else:

        condition = f"""<and>
  <vargte respident="response1">{clean_number(rule["low"])}</vargte>
  <varlte respident="response1">{clean_number(rule["high"])}</varlte>
</and>"""

    processing = resprocessing(
        [
            score_condition(
                condition
            )
        ]
    )

    return (
        presentation_extra,
        processing,
        "1",
    )


# =========================================================
# CANVAS ITEM
# =========================================================

def generate_item_xml(
    question,
    quiz_ident,
    item_index,
):

     # -----------------------------------------------------
    # MATH VALIDATION
    # -----------------------------------------------------

    math_problems = validate_question_math(
        question
    )

    if math_problems:
        raise ValueError(
            f"Question {question.get('number')} "
            "contains invalid mathematical content: "
            + "; ".join(math_problems)
        )
    
    question_type = question.get(
        "type"
    )

    if question_type not in CANVAS_TYPES:
        raise ValueError(
            f"Unsupported question type: "
            f"{question_type}"
        )

    question_number = question.get(
        "number",
        item_index + 1,
    )

    # Stable Canvas-style item identifier.
    item_ident = hash_ident(
        f"{quiz_ident}:question:{question_number}"
    )

    assessment_question_identifier = (
        hash_ident(
            f"{item_ident}:question"
        )
    )

    answer_base = (
        (item_index + 1)
        * 1000
    )

    # -----------------------------------------------------
    # PRESENTATION + SCORING
    # -----------------------------------------------------

    if question_type in {
        "multiple_choice",
        "multiple_answer",
    }:

        (
            presentation_extra,
            processing,
            answer_ids,
        ) = choice_question_xml(
            question,
            item_ident,
            answer_base,
        )

    elif question_type == "numeric":

        (
            presentation_extra,
            processing,
            answer_ids,
        ) = numeric_question_xml(
            question
        )

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    fields = [
        meta_field(
            "question_type",
            CANVAS_TYPES[
                question_type
            ],
        ),
        meta_field(
            "points_possible",
            clean_number(
                get_points(
                    question
                )
            ),
        ),
        meta_field(
            "original_answer_ids",
            answer_ids,
        ),
        meta_field(
            "assessment_question_identifierref",
            assessment_question_identifier,
        ),
        meta_field(
            "calculator_type",
            "none",
        ),
    ]

    metadata = (
        "<itemmetadata>\n"
        "<qtimetadata>\n"
        + "\n".join(fields)
        + "\n</qtimetadata>\n"
        "</itemmetadata>"
    )

    # -----------------------------------------------------
    # QUESTION TEXT
    # -----------------------------------------------------

    question_html = render_prompt(
        question
    )

    question_material = f"""<material>
  <mattext texttype="text/html"><![CDATA[{question_html}]]></mattext>
</material>"""

    presentation = (
        "<presentation>\n"
        + question_material
        + "\n"
        + presentation_extra
        + "\n</presentation>"
    )

    # -----------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------

    feedback = get_feedback(
        question
    )

    feedback_parts = []

    if feedback["correct"]:
        feedback_parts.append(
            feedback_xml(
                "correct_fb",
                feedback["correct"],
            )
        )

    if feedback["general"]:
        feedback_parts.append(
            feedback_xml(
                "general_fb",
                feedback["general"],
            )
        )

    if feedback["incorrect"]:
        feedback_parts.append(
            feedback_xml(
                "general_incorrect_fb",
                feedback["incorrect"],
            )
        )

    # -----------------------------------------------------
    # ITEM
    # -----------------------------------------------------

    title = question.get(
        "title"
    )

    if not title:
        title = (
            f"Question {question_number}"
        )

    parts = [
        metadata,
        presentation,
        processing,
        *feedback_parts,
    ]

    return f"""<item
    ident="{item_ident}"
    title="{xml_escape(title)}">
{"".join(parts)}
</item>"""


# =========================================================
# FULL ASSESSMENT
# =========================================================

def generate_assessment_xml(
    quiz_data,
    quiz_ident=None,
    settings=None,
):
    """
    Build the complete Canvas QTI assessment.

    The reference exporter also places cc_maxattempts
    metadata directly on the assessment.
    """

    if quiz_ident is None:
        quiz_ident = random_ident()

    if settings is None:
        settings = {}

    title = quiz_data.get(
        "title",
        "CourseCraft Quiz",
    )

    allowed_attempts = settings.get(
        "allowed_attempts",
        1,
    )

    if allowed_attempts < 0:
        attempts_value = "unlimited"
    else:
        attempts_value = str(
            allowed_attempts
        )

    items = []

    for index, question in enumerate(
        quiz_data.get(
            "questions",
            [],
        )
    ):

        items.append(
            generate_item_xml(
                question,
                quiz_ident,
                index,
            )
        )

    items_xml = "\n".join(
        items
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop {QTI_NAMESPACE}>
  <assessment
      ident="{quiz_ident}"
      title="{xml_escape(title)}">

    <qtimetadata>
      <qtimetadatafield>
        <fieldlabel>cc_maxattempts</fieldlabel>
        <fieldentry>{xml_escape(attempts_value)}</fieldentry>
      </qtimetadatafield>
    </qtimetadata>

    <section ident="root_section">
{items_xml}
    </section>

  </assessment>
</questestinterop>
"""