import uuid

from xml.sax.saxutils import escape


# =========================================================
# POINTS
# =========================================================

def get_points(question):
    """
    Return the point value for a question.

    - Explicit zero-point questions remain 0.
    - If points are missing, default to 1 for the MVP.
    """

    if question.get("zero_point"):
        return 0

    points = question.get("points")

    if points is None:
        return 1

    return points


# =========================================================
# CHOICES
# =========================================================

def build_choices(question):
    """
    Build QTI response_label elements for choice questions.

    Returns:
        choice_xml
        correct_ids
        incorrect_ids
    """

    choice_xml = ""
    correct_ids = []
    incorrect_ids = []

    for index, choice in enumerate(
        question.get("choices", [])
    ):

        # A, B, C, D...
        choice_id = chr(65 + index)

        choice_text = escape(
            str(
                choice.get(
                    "text",
                    "",
                )
            )
        )

        choice_xml += f"""
                            <response_label ident="{choice_id}">
                                <material>
                                    <mattext texttype="text/html">{choice_text}</mattext>
                                </material>
                            </response_label>
"""

        if choice.get("correct"):
            correct_ids.append(
                choice_id
            )
        else:
            incorrect_ids.append(
                choice_id
            )

    return (
        choice_xml,
        correct_ids,
        incorrect_ids,
    )


# =========================================================
# MULTIPLE CHOICE
# =========================================================

def generate_multiple_choice_question(question):

    number = question["number"]

    # Canvas-style unique question reference.
    question_identifier = uuid.uuid4().hex

    prompt = escape(
        str(
            question.get(
                "prompt",
                "",
            )
        )
    )

    points = get_points(
        question
    )

    (
        choice_xml,
        correct_ids,
        incorrect_ids,
    ) = build_choices(
        question
    )

    if len(correct_ids) != 1:

        raise ValueError(
            f"Question {number} must have exactly "
            "one correct answer."
        )

    correct_id = correct_ids[0]

    return f"""
            <item
                ident="q{number}"
                title="Question {number}">

                <itemmetadata>
                    <qtimetadata>

                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>multiple_choice_question</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{points}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>assessment_question_identifierref</fieldlabel>
                            <fieldentry>{question_identifier}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>calculator_type</fieldlabel>
                            <fieldentry>none</fieldentry>
                        </qtimetadatafield>

                    </qtimetadata>
                </itemmetadata>

                <presentation>

                    <material>
                        <mattext texttype="text/html">{prompt}</mattext>
                    </material>

                    <response_lid
                        ident="response{number}"
                        rcardinality="Single">

                        <render_choice>

{choice_xml}

                        </render_choice>

                    </response_lid>

                </presentation>

                <resprocessing>

                    <outcomes>

                        <decvar
                            varname="SCORE"
                            vartype="Decimal"
                            minvalue="0"
                            maxvalue="100"/>

                    </outcomes>

                    <respcondition continue="No">

                        <conditionvar>

                            <varequal
                                respident="response{number}">{correct_id}</varequal>

                        </conditionvar>

                        <setvar
                            varname="SCORE"
                            action="Set">100</setvar>

                    </respcondition>

                </resprocessing>

            </item>
"""


# =========================================================
# MULTIPLE ANSWER
# =========================================================

def generate_multiple_answer_question(question):

    number = question["number"]

    question_identifier = uuid.uuid4().hex

    prompt = escape(
        str(
            question.get(
                "prompt",
                "",
            )
        )
    )

    points = get_points(
        question
    )

    (
        choice_xml,
        correct_ids,
        incorrect_ids,
    ) = build_choices(
        question
    )

    if not correct_ids:

        raise ValueError(
            f"Question {number} has no correct answers."
        )

    conditions = ""

    # Every correct choice must be selected.
    for choice_id in correct_ids:

        conditions += f"""
                                <varequal
                                    respident="response{number}">{choice_id}</varequal>
"""

    # Every incorrect choice must NOT be selected.
    for choice_id in incorrect_ids:

        conditions += f"""
                                <not>
                                    <varequal
                                        respident="response{number}">{choice_id}</varequal>
                                </not>
"""

    return f"""
            <item
                ident="q{number}"
                title="Question {number}">

                <itemmetadata>
                    <qtimetadata>

                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>multiple_answers_question</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{points}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>assessment_question_identifierref</fieldlabel>
                            <fieldentry>{question_identifier}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>calculator_type</fieldlabel>
                            <fieldentry>none</fieldentry>
                        </qtimetadatafield>

                    </qtimetadata>
                </itemmetadata>

                <presentation>

                    <material>
                        <mattext texttype="text/html">{prompt}</mattext>
                    </material>

                    <response_lid
                        ident="response{number}"
                        rcardinality="Multiple">

                        <render_choice>

{choice_xml}

                        </render_choice>

                    </response_lid>

                </presentation>

                <resprocessing>

                    <outcomes>

                        <decvar
                            varname="SCORE"
                            vartype="Decimal"
                            minvalue="0"
                            maxvalue="100"/>

                    </outcomes>

                    <respcondition continue="No">

                        <conditionvar>

                            <and>

{conditions}

                            </and>

                        </conditionvar>

                        <setvar
                            varname="SCORE"
                            action="Set">100</setvar>

                    </respcondition>

                </resprocessing>

            </item>
"""


# =========================================================
# NUMERIC
# =========================================================

def generate_numeric_question(question):
    """
    Generate a Canvas-style QTI numerical question.

    We are currently matching the known-good Canvas
    numeric export using an exact numeric answer.

    Canvas-compatible tolerance will be added after
    exact numeric import is proven.
    """

    number = question["number"]

    # This was the metadata field missing from our
    # previous CourseCraft numeric output.
    question_identifier = uuid.uuid4().hex

    prompt = escape(
        str(
            question.get(
                "prompt",
                "",
            )
        )
    )

    points = get_points(
        question
    )

    answer = question.get(
        "numeric_answer"
    )

    if answer is None:

        raise ValueError(
            f"Question {number} has no numeric answer."
        )

    return f"""
            <item
                ident="q{number}"
                title="Question {number}">

                <itemmetadata>
                    <qtimetadata>

                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>numerical_question</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{points}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>original_answer_ids</fieldlabel>
                            <fieldentry>1</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>assessment_question_identifierref</fieldlabel>
                            <fieldentry>{question_identifier}</fieldentry>
                        </qtimetadatafield>

                        <qtimetadatafield>
                            <fieldlabel>calculator_type</fieldlabel>
                            <fieldentry>none</fieldentry>
                        </qtimetadatafield>

                    </qtimetadata>
                </itemmetadata>

                <presentation>

                    <material>

                        <mattext texttype="text/html">{prompt}</mattext>

                    </material>

                    <response_str
                        ident="response1"
                        rcardinality="Single">

                        <render_fib fibtype="Decimal">

                            <response_label
                                ident="answer1"/>

                        </render_fib>

                    </response_str>

                </presentation>

                <resprocessing>

                    <outcomes>

                        <decvar
                            varname="SCORE"
                            vartype="Decimal"
                            minvalue="0"
                            maxvalue="100"/>

                    </outcomes>

                    <respcondition continue="No">

                        <conditionvar>

                            <or>

                                <varequal
                                    respident="response1">{answer}</varequal>

                                <and>

                                    <vargte
                                        respident="response1">{answer}</vargte>

                                    <varlte
                                        respident="response1">{answer}</varlte>

                                </and>

                            </or>

                        </conditionvar>

                        <setvar
                            varname="SCORE"
                            action="Set">100</setvar>

                    </respcondition>

                </resprocessing>

            </item>
"""


# =========================================================
# QUESTION ROUTER
# =========================================================

def generate_question_xml(question):
    """
    Send each CourseCraft question to the correct
    QTI generator.
    """

    question_type = question.get(
        "type"
    )

    if question_type == "multiple_choice":

        return generate_multiple_choice_question(
            question
        )

    if question_type == "multiple_answer":

        return generate_multiple_answer_question(
            question
        )

    if question_type == "numeric":

        return generate_numeric_question(
            question
        )

    raise ValueError(
        f"Unsupported question type: "
        f"{question_type}"
    )


# =========================================================
# FULL ASSESSMENT
# =========================================================

def generate_assessment_xml(quiz_data):
    """
    Generate the complete QTI assessment containing
    all CourseCraft questions.
    """

    title = escape(
        str(
            quiz_data.get(
                "title",
                "CourseCraft Quiz",
            )
        )
    )

    items = []

    for question in quiz_data.get(
        "questions",
        []
    ):

        items.append(
            generate_question_xml(
                question
            )
        )

    items_xml = "\n".join(
        items
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>

<questestinterop
    xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="
        http://www.imsglobal.org/xsd/ims_qtiasiv1p2
        http://www.imsglobal.org/xsd/ims_qtiasiv1p2/ims_qtiasiv1p2.xsd">

    <assessment
        ident="coursecraft_assessment"
        title="{title}">

        <section ident="root_section">

{items_xml}

        </section>

    </assessment>

</questestinterop>
"""