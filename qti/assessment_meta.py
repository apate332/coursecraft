from xml.sax.saxutils import escape


def generate_assessment_meta_xml(
    quiz_data,
    assessment_id,
):
    title = escape(
        str(
            quiz_data.get(
                "title",
                "CourseCraft Quiz",
            )
        )
    )

    questions = quiz_data.get(
        "questions",
        []
    )

    total_points = 0

    for question in questions:

        if question.get("zero_point"):
            points = 0
        else:
            points = question.get("points")

            if points is None:
                points = 1

        total_points += points

    return f"""<?xml version="1.0" encoding="UTF-8"?>

<quiz
    identifier="{assessment_id}">

    <title>{title}</title>

    <description></description>

    <quiz_type>assignment</quiz_type>

    <points_possible>{total_points}</points_possible>

    <shuffle_answers>false</shuffle_answers>

    <hide_results></hide_results>

    <show_correct_answers>true</show_correct_answers>

    <one_question_at_a_time>false</one_question_at_a_time>

    <cant_go_back>false</cant_go_back>

    <allowed_attempts>1</allowed_attempts>

    <scoring_policy>keep_highest</scoring_policy>

    <calculator_type>none</calculator_type>

</quiz>
"""