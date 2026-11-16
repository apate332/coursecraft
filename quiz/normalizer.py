import copy


def normalize_question(question):
    """
    Normalize obvious structural inconsistencies in AI output.

    This function may correct structure when the intended
    meaning is unambiguous.

    It must NOT invent answers or curriculum content.
    """

    question = copy.deepcopy(question)

    question_type = question.get("type")
    choices = question.get("choices") or []

    correct_choices = [
        choice
        for choice in choices
        if choice.get("correct") is True
    ]

    changes = []

    # -----------------------------------------------------
    # MULTIPLE CHOICE WITH MULTIPLE CORRECT ANSWERS
    # -----------------------------------------------------

    if (
        question_type == "multiple_choice"
        and len(correct_choices) > 1
    ):
        question["type"] = "multiple_answer"

        changes.append(
            "Changed question type from Multiple Choice "
            "to Multiple Answer because more than one "
            "answer is marked correct."
        )

    # -----------------------------------------------------
    # ZERO-POINT NORMALIZATION
    # -----------------------------------------------------

    if question.get("zero_point") is True:
        question["points"] = 0

    elif question.get("points") == 0:
        question["zero_point"] = True

    # -----------------------------------------------------
    # STORE NORMALIZATION INFORMATION
    # -----------------------------------------------------

    question["_normalization_changes"] = changes

    return question


def normalize_quiz(quiz_data):
    """
    Normalize every question while preserving the
    original quiz title and other quiz-level data.
    """

    normalized = copy.deepcopy(quiz_data)

    normalized["questions"] = [
        normalize_question(question)
        for question in quiz_data.get(
            "questions",
            []
        )
    ]

    return normalized