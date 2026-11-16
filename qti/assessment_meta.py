import html


# =========================================================
# HELPERS
# =========================================================

def xml_escape(value):
    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def clean_number(value):
    if value is None:
        return "0"

    number = float(value)

    if number.is_integer():
        return str(int(number))

    return format(
        number,
        ".12g",
    )


def bool_text(value):
    return "true" if value else "false"


def question_points(question):
    if question.get("zero_point"):
        return 0

    points = question.get("points")

    if points is None:
        return 1

    return points


# =========================================================
# DEFAULT CANVAS SETTINGS
# =========================================================

DEFAULT_SETTINGS = {
    "description": "",
    "shuffle_questions": False,
    "shuffle_answers": False,
    "show_correct_answers": False,
    "allowed_attempts": 1,
    "one_question_at_a_time": False,
    "cant_go_back": False,
    "calculator": "none",
}


# =========================================================
# ASSESSMENT META XML
# =========================================================

def generate_assessment_meta_xml(
    quiz_data,
    quiz_ident,
    settings=None,
):
    """
    Generate Canvas assessment_meta.xml.

    This follows the Canvas New Quizzes metadata structure
    used by the working reference exporter.
    """

    final_settings = {
        **DEFAULT_SETTINGS,
        **(settings or {}),
    }

    title = quiz_data.get(
        "title",
        "CourseCraft Quiz",
    )

    questions = quiz_data.get(
        "questions",
        [],
    )

    total_points = sum(
        question_points(question)
        for question in questions
    )

    description = final_settings.get(
        "description",
        "",
    )

    shuffle_questions = final_settings.get(
        "shuffle_questions",
        False,
    )

    shuffle_answers = final_settings.get(
        "shuffle_answers",
        False,
    )

    calculator = final_settings.get(
        "calculator",
        "none",
    )

    show_correct_answers = final_settings.get(
        "show_correct_answers",
        False,
    )

    allowed_attempts = final_settings.get(
        "allowed_attempts",
        1,
    )

    one_question_at_a_time = final_settings.get(
        "one_question_at_a_time",
        False,
    )

    cant_go_back = final_settings.get(
        "cant_go_back",
        False,
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<quiz
    identifier="{xml_escape(quiz_ident)}"
    xmlns="http://canvas.instructure.com/xsd/cccv1p0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://canvas.instructure.com/xsd/cccv1p0 https://canvas.instructure.com/xsd/cccv1p0.xsd">

  <title>{xml_escape(title)}</title>

  <description>{xml_escape(description)}</description>

  <due_at/>
  <lock_at/>
  <unlock_at/>

  <shuffle_questions>{bool_text(shuffle_questions)}</shuffle_questions>

  <shuffle_answers>{bool_text(shuffle_answers)}</shuffle_answers>

  <calculator_type>{xml_escape(calculator)}</calculator_type>

  <scoring_policy>keep_highest</scoring_policy>

  <hide_results/>

  <quiz_type>assignment</quiz_type>

  <points_possible>{clean_number(total_points)}</points_possible>

  <require_lockdown_browser>false</require_lockdown_browser>

  <require_lockdown_browser_for_results>false</require_lockdown_browser_for_results>

  <require_lockdown_browser_monitor>false</require_lockdown_browser_monitor>

  <lockdown_browser_monitor_data/>

  <show_correct_answers>{bool_text(show_correct_answers)}</show_correct_answers>

  <anonymous_submissions>false</anonymous_submissions>

  <could_be_locked>false</could_be_locked>

  <disable_timer_autosubmission>false</disable_timer_autosubmission>

  <allowed_attempts>{allowed_attempts}</allowed_attempts>

  <build_on_last_attempt>false</build_on_last_attempt>

  <one_question_at_a_time>{bool_text(one_question_at_a_time)}</one_question_at_a_time>

  <cant_go_back>{bool_text(cant_go_back)}</cant_go_back>

  <available>false</available>

  <one_time_results>false</one_time_results>

  <show_correct_answers_last_attempt>false</show_correct_answers_last_attempt>

  <only_visible_to_overrides>false</only_visible_to_overrides>

  <module_locked>false</module_locked>

  <allow_clear_mc_selection>true</allow_clear_mc_selection>

  <disable_document_access>false</disable_document_access>

  <result_view_restricted>true</result_view_restricted>

  <display_items>true</display_items>

  <display_item_feedback>true</display_item_feedback>

  <display_item_response>true</display_item_response>

  <display_points_awarded>true</display_points_awarded>

  <display_points_possible>true</display_points_possible>

  <display_item_correct_answer>{bool_text(show_correct_answers)}</display_item_correct_answer>

  <display_item_response_correctness>true</display_item_response_correctness>

</quiz>
"""