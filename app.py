import json
import os
import tempfile

import streamlit as st

from ai.client import ask_asu_ai
from document.extractor import extract_docx
from document.chunker import chunk_document
from quiz.normalizer import normalize_quiz
from qti.package import create_qti_package
from qti.validator import validate_qti_package


PROMPT_PATH = "prompts/quiz_converter.txt"


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="CourseCraft",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# SESSION STATE
# =========================================================

if "workspace" not in st.session_state:
    st.session_state.workspace = "Create Quiz"

if "selected_question" not in st.session_state:
    st.session_state.selected_question = 0


# =========================================================
# DESIGN SYSTEM
# =========================================================

st.markdown(
    """
    <style>

    /* -----------------------------------------------
       APPLICATION
       ----------------------------------------------- */

    .stApp {
        background: #f5f5f4;
        color: #202020;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }

    /* -----------------------------------------------
       SIDEBAR
       ----------------------------------------------- */

    section[data-testid="stSidebar"] {
        background: #202020;
        border-right: 1px solid #303030;
    }

    section[data-testid="stSidebar"] > div {
        background: #202020;
    }

    section[data-testid="stSidebar"] * {
        color: #f5f5f5;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #3a3a3a;
    }

    section[data-testid="stSidebar"] button {
        border-radius: 8px;
    }

    /* -----------------------------------------------
       TYPOGRAPHY
       ----------------------------------------------- */

    h1, h2, h3 {
        color: #202020;
        letter-spacing: -0.025em;
    }

    h1 {
        font-size: 2.35rem !important;
        font-weight: 720 !important;
    }

    h2 {
        font-size: 1.55rem !important;
        font-weight: 680 !important;
    }

    h3 {
        font-size: 1.15rem !important;
        font-weight: 650 !important;
    }

    p {
        line-height: 1.55;
    }

    /* -----------------------------------------------
       BUTTONS
       ----------------------------------------------- */

    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 8px;
        min-height: 2.75rem;
        font-weight: 650;
        border: 1px solid #d8d8d8;
        transition: all 0.15s ease;
    }

    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background: #c65d28;
        border-color: #c65d28;
        color: #ffffff;
    }

    div.stButton > button[kind="primary"]:hover,
    div.stDownloadButton > button[kind="primary"]:hover {
        background: #a94b1f;
        border-color: #a94b1f;
        color: #ffffff;
    }

    /* -----------------------------------------------
       INPUTS
       ----------------------------------------------- */

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        border-radius: 8px;
    }

    /* -----------------------------------------------
       FILE UPLOADER
       ----------------------------------------------- */

    section[data-testid="stFileUploaderDropzone"] {
        background: #ffffff;
        border: 1.5px dashed #a7a7a7;
        border-radius: 12px;
        padding: 1.2rem;
    }

    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: #c65d28;
    }

    /* -----------------------------------------------
       METRICS
       ----------------------------------------------- */

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e2e2;
        border-radius: 10px;
        padding: 1rem 1.1rem;
    }

    div[data-testid="stMetricLabel"] {
        color: #717171;
    }

    div[data-testid="stMetricValue"] {
        color: #202020;
    }

    /* -----------------------------------------------
       STATUS / ALERTS
       ----------------------------------------------- */

    div[data-testid="stAlert"] {
        border-radius: 9px;
    }

    /* -----------------------------------------------
       CUSTOM UI
       ----------------------------------------------- */

    .cc-eyebrow {
        color: #c65d28;
        font-size: 0.78rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.35rem;
    }

    .cc-subtitle {
        color: #6c6c6c;
        font-size: 1.05rem;
        max-width: 720px;
        margin-top: -0.3rem;
        margin-bottom: 1.8rem;
    }

    .cc-panel {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.35rem;
        margin-bottom: 1rem;
    }

    .cc-status {
        display: inline-block;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: #eeeeec;
        color: #555555;
        font-size: 0.78rem;
        font-weight: 650;
    }

    .cc-type {
        color: #c65d28;
        font-size: 0.78rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .cc-help {
        color: #777777;
        font-size: 0.88rem;
    }

    .cc-divider {
        height: 1px;
        background: #e0e0e0;
        margin: 1.5rem 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================

def pretty_type(question_type):
    labels = {
        "multiple_choice": "Multiple Choice",
        "multiple_answer": "Multiple Answer",
        "numeric": "Numeric",
    }

    return labels.get(
        question_type,
        question_type.replace("_", " ").title(),
    )


def question_points(question):
    if question.get("zero_point"):
        return 0

    points = question.get("points")

    if points is None:
        return 1

    return points


def reset_quiz():
    for key in [
        "quiz_data",
        "qti_zip",
        "qti_filename",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state.selected_question = 0


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            font-size:1.65rem;
            font-weight:750;
            margin-bottom:0.15rem;
        ">
            CourseCraft
        </div>

        <div style="
            color:#a9a9a9;
            font-size:0.84rem;
            margin-bottom:1.5rem;
        ">
            Canvas quiz workspace
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "New Quiz",
        use_container_width=True,
        type="primary",
    ):
        reset_quiz()
        st.session_state.workspace = "Create Quiz"
        st.rerun()

    st.markdown("---")

    st.caption("WORKFLOW")

    if st.button(
        "Create Quiz",
        use_container_width=True,
    ):
        st.session_state.workspace = "Create Quiz"

    if st.button(
        "Review",
        use_container_width=True,
        disabled="quiz_data" not in st.session_state,
    ):
        st.session_state.workspace = "Review"

    if st.button(
        "Validate",
        use_container_width=True,
        disabled="quiz_data" not in st.session_state,
    ):
        st.session_state.workspace = "Validate"

    if st.button(
        "Export",
        use_container_width=True,
        disabled="quiz_data" not in st.session_state,
    ):
        st.session_state.workspace = "Export"

    st.markdown("---")

    st.caption("PROJECT")

    st.markdown(
        """
        <div style="
            color:#bdbdbd;
            font-size:0.84rem;
            line-height:1.6;
        ">
            Generate Canvas resources for review
            and testing in a DEV shell before use
            in an instructional course.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# CREATE QUIZ
# =========================================================

if st.session_state.workspace == "Create Quiz":

    st.markdown(
        '<div class="cc-eyebrow">Create</div>',
        unsafe_allow_html=True,
    )

    st.title("Create a Canvas Quiz")

    st.markdown(
        """
        <div class="cc-subtitle">
            Upload curriculum and let CourseCraft analyze,
            structure, and prepare the questions for Canvas.
        </div>
        """,
        unsafe_allow_html=True,
    )

    source = st.radio(
        "Source",
        [
            "Word Document",
            "Google Doc",
        ],
        horizontal=True,
    )

    if source == "Word Document":

        st.markdown(
            """
            <div class="cc-panel">
                <div style="
                    font-size:1.05rem;
                    font-weight:650;
                    margin-bottom:0.25rem;
                ">
                    Curriculum document
                </div>
                <div class="cc-help">
                    Upload a .docx curriculum or assignment document.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Upload Word document",
            type=["docx"],
            label_visibility="collapsed",
        )

        if uploaded_file:

            st.success(
                f"{uploaded_file.name} is ready to analyze."
            )

            if st.button(
                "Analyze Document",
                type="primary",
                use_container_width=False,
            ):

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".docx",
                ) as temp_file:

                    temp_file.write(
                        uploaded_file.getbuffer()
                    )

                    temp_path = temp_file.name

                try:

                    status = st.status(
                        "Analyzing curriculum",
                        expanded=True,
                    )

                    status.write(
                        "Extracting document content..."
                    )

                    content = extract_docx(
                        temp_path
                    )

                    status.write(
                        "Document extracted."
                    )

                    chunks = chunk_document(
                        content,
                        max_chars=6000,
                        overlap_chars=1200,
                    )

                    status.write(
                        f"Prepared {len(chunks)} sections."
                    )

                    with open(
                        PROMPT_PATH,
                        "r",
                        encoding="utf-8",
                    ) as file:

                        instructions = file.read()

                    all_questions = {}

                    progress = st.progress(0)

                    for index, chunk in enumerate(
                        chunks,
                        start=1,
                    ):

                        status.update(
                            label=(
                                "Analyzing with ASU AI — "
                                f"section {index} of "
                                f"{len(chunks)}"
                            ),
                            state="running",
                            expanded=True,
                        )

                        prompt = f"""
{instructions}

This is section {index} of {len(chunks)}
from one larger curriculum document.

Extract quiz questions that are sufficiently
represented in this section.

Sections overlap, so a question may also appear
in another section.

Do not invent missing information.

SOURCE CURRICULUM
==============================

{chunk}

==============================
END SOURCE CURRICULUM
"""

                        response = ask_asu_ai(
                            prompt
                        )

                        chunk_data = json.loads(
                            response["response"]
                        )

                        for question in chunk_data.get(
                            "questions",
                            [],
                        ):

                            number = question.get(
                                "number"
                            )

                            if number is not None:
                                all_questions[
                                    number
                                ] = question

                        progress.progress(
                            index / len(chunks)
                        )

                    questions = [
                        all_questions[number]
                        for number in sorted(
                            all_questions
                        )
                    ]

                    quiz_data = {
                        "title": os.path.splitext(
                            uploaded_file.name
                        )[0],
                        "questions": questions,
                    }

                    st.session_state[
                        "quiz_data"
                    ] = quiz_data

                    st.session_state[
                        "selected_question"
                    ] = 0

                    if "qti_zip" in st.session_state:
                        del st.session_state["qti_zip"]

                    if "qti_filename" in st.session_state:
                        del st.session_state[
                            "qti_filename"
                        ]

                    status.update(
                        label="Analysis complete",
                        state="complete",
                        expanded=False,
                    )

                    st.session_state.workspace = "Review"

                    st.rerun()

                finally:

                    if os.path.exists(
                        temp_path
                    ):
                        os.remove(
                            temp_path
                        )

    else:

        st.markdown(
            """
            <div class="cc-panel">
                <div style="
                    font-size:1.05rem;
                    font-weight:650;
                    margin-bottom:0.25rem;
                ">
                    Google Doc
                </div>
                <div class="cc-help">
                    Google Doc import is planned for the
                    next version.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        google_url = st.text_input(
            "Google Doc URL",
            placeholder=(
                "https://docs.google.com/document/d/..."
            ),
        )

        st.info(
            "Google Doc import is not connected yet."
        )


# =========================================================
# REVIEW
# =========================================================

elif st.session_state.workspace == "Review":

    if "quiz_data" not in st.session_state:

        st.warning(
            "Analyze a document before reviewing a quiz."
        )

    else:

        quiz = st.session_state["quiz_data"]
        questions = quiz["questions"]

        multiple_choice = sum(
            q.get("type") == "multiple_choice"
            for q in questions
        )

        multiple_answer = sum(
            q.get("type") == "multiple_answer"
            for q in questions
        )

        numeric = sum(
            q.get("type") == "numeric"
            for q in questions
        )

        st.markdown(
            '<div class="cc-eyebrow">Review</div>',
            unsafe_allow_html=True,
        )

        title_col, status_col = st.columns(
            [5, 1]
        )

        with title_col:
            st.title(
                quiz["title"]
            )

            st.markdown(
                """
                <div class="cc-subtitle">
                    Review the AI-generated quiz before
                    creating the Canvas package.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with status_col:
            st.markdown(
                """
                <div style="padding-top:0.8rem;">
                    <span class="cc-status">
                        Ready for review
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        stat1, stat2, stat3, stat4 = st.columns(
            4
        )

        stat1.metric(
            "Questions",
            len(questions),
        )

        stat2.metric(
            "Multiple Choice",
            multiple_choice,
        )

        stat3.metric(
            "Multiple Answer",
            multiple_answer,
        )

        stat4.metric(
            "Numeric",
            numeric,
        )

        st.markdown(
            '<div class="cc-divider"></div>',
            unsafe_allow_html=True,
        )

        left, right = st.columns(
            [1.05, 2.4],
            gap="large",
        )

        # -------------------------------------------------
        # QUESTION LIST
        # -------------------------------------------------

        with left:

            st.subheader(
                "Questions"
            )

            st.caption(
                "Select a question to review."
            )

            question_labels = [
                (
                    f"{int(q['number']):02d}   "
                    f"{pretty_type(q.get('type', ''))}"
                )
                for q in questions
            ]

            selected_label = st.radio(
                "Question list",
                question_labels,
                index=min(
                    st.session_state[
                        "selected_question"
                    ],
                    len(question_labels) - 1,
                ),
                label_visibility="collapsed",
            )

            selected_index = (
                question_labels.index(
                    selected_label
                )
            )

            st.session_state[
                "selected_question"
            ] = selected_index

        # -------------------------------------------------
        # QUESTION EDITOR
        # -------------------------------------------------

        with right:

            question = questions[
                st.session_state[
                    "selected_question"
                ]
            ]

            number = question["number"]

            st.markdown(
                f"""
                <div class="cc-panel">
                    <div class="cc-type">
                        {pretty_type(question.get("type", ""))}
                    </div>

                    <div style="
                        font-size:1.35rem;
                        font-weight:700;
                        margin-top:0.35rem;
                    ">
                        Question {number}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            prompt = st.text_area(
                "Question",
                value=question.get(
                    "prompt",
                    "",
                ),
                height=130,
                key=f"prompt_{number}",
            )

            question["prompt"] = prompt

            # ---------------------------------------------
            # CHOICE QUESTIONS
            # ---------------------------------------------

            if question.get("type") in [
                "multiple_choice",
                "multiple_answer",
            ]:

                st.subheader(
                    "Answer choices"
                )

                choices = question.get(
                    "choices",
                    [],
                )

                for index, choice in enumerate(
                    choices
                ):

                    choice_col, correct_col = st.columns(
                        [5, 1]
                    )

                    with choice_col:

                        new_text = st.text_input(
                            f"Choice {index + 1}",
                            value=choice.get(
                                "text",
                                "",
                            ),
                            key=(
                                f"choice_{number}_"
                                f"{index}"
                            ),
                        )

                        choice["text"] = new_text

                    with correct_col:

                        is_correct = st.checkbox(
                            "Correct",
                            value=bool(
                                choice.get(
                                    "correct"
                                )
                            ),
                            key=(
                                f"correct_{number}_"
                                f"{index}"
                            ),
                        )

                        choice[
                            "correct"
                        ] = is_correct

            # ---------------------------------------------
            # NUMERIC
            # ---------------------------------------------

            elif question.get(
                "type"
            ) == "numeric":

                st.subheader(
                    "Numeric answer"
                )

                numeric_col1, numeric_col2 = st.columns(
                    2
                )

                with numeric_col1:

                    answer = st.number_input(
                        "Correct answer",
                        value=float(
                            question.get(
                                "numeric_answer"
                            )
                            or 0
                        ),
                        key=f"numeric_answer_{number}",
                    )

                    question[
                        "numeric_answer"
                    ] = answer

                with numeric_col2:

                    tolerance = st.number_input(
                        "Tolerance",
                        min_value=0.0,
                        value=float(
                            question.get(
                                "numeric_tolerance"
                            )
                            or 0
                        ),
                        key=f"numeric_tolerance_{number}",
                    )

                    question[
                        "numeric_tolerance"
                    ] = tolerance

            # ---------------------------------------------
            # POINTS
            # ---------------------------------------------

            st.subheader(
                "Question settings"
            )

            settings_col1, settings_col2 = st.columns(
                2
            )

            with settings_col1:

                current_points = question_points(
                    question
                )

                points = st.number_input(
                    "Points",
                    min_value=0.0,
                    value=float(
                        current_points
                    ),
                    step=1.0,
                    key=f"points_{number}",
                )

                question[
                    "points"
                ] = points

                question[
                    "zero_point"
                ] = points == 0

            with settings_col2:

                st.text_input(
                    "Question type",
                    value=pretty_type(
                        question.get(
                            "type",
                            "",
                        )
                    ),
                    disabled=True,
                    key=f"type_{number}",
                )

            # ---------------------------------------------
            # FEEDBACK
            # ---------------------------------------------

            feedback_value = question.get(
                "feedback"
            )

            if isinstance(
                feedback_value,
                dict,
            ):
                feedback_value = (
                    feedback_value.get(
                        "general"
                    )
                    or feedback_value.get(
                        "correct"
                    )
                    or ""
                )

            feedback = st.text_area(
                "Feedback",
                value=feedback_value or "",
                height=120,
                key=f"feedback_{number}",
            )

            question[
                "feedback"
            ] = feedback

            st.success(
                "Changes are kept in this session."
            )

        st.markdown(
            '<div class="cc-divider"></div>',
            unsafe_allow_html=True,
        )

        action1, action2 = st.columns(
            [1, 1]
        )

        with action1:

            if st.button(
                "Validate Quiz",
                use_container_width=True,
            ):
                st.session_state.workspace = "Validate"
                st.rerun()

        with action2:

            if st.button(
                "Continue to Export",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.workspace = "Export"
                st.rerun()


# =========================================================
# VALIDATE
# =========================================================

elif st.session_state.workspace == "Validate":

    if "quiz_data" not in st.session_state:

        st.warning(
            "Analyze a document before validating."
        )

    else:

        quiz = st.session_state["quiz_data"]
        questions = quiz["questions"]

        st.markdown(
            '<div class="cc-eyebrow">Validate</div>',
            unsafe_allow_html=True,
        )

        st.title(
            "Quiz Validation"
        )

        st.markdown(
            """
            <div class="cc-subtitle">
                Check the quiz for missing answers,
                point values, and other issues before export.
            </div>
            """,
            unsafe_allow_html=True,
        )

        issues = []

        for question in questions:

            number = question.get(
                "number"
            )

            question_type = question.get(
                "type"
            )

            if not question.get(
                "prompt"
            ):
                issues.append(
                    f"Question {number}: "
                    "question text is missing."
                )

            if question_type == "multiple_choice":

                correct_count = sum(
                    bool(
                        choice.get(
                            "correct"
                        )
                    )
                    for choice in question.get(
                        "choices",
                        [],
                    )
                )

                if correct_count != 1:
                    issues.append(
                        f"Question {number}: "
                        "Multiple Choice requires "
                        "exactly one correct answer."
                    )

            elif question_type == "multiple_answer":

                correct_count = sum(
                    bool(
                        choice.get(
                            "correct"
                        )
                    )
                    for choice in question.get(
                        "choices",
                        [],
                    )
                )

                if correct_count < 1:
                    issues.append(
                        f"Question {number}: "
                        "Multiple Answer has no "
                        "correct answer selected."
                    )

            elif question_type == "numeric":

                if question.get(
                    "numeric_answer"
                ) is None:
                    issues.append(
                        f"Question {number}: "
                        "numeric answer is missing."
                    )

        if issues:

            st.warning(
                f"{len(issues)} issue(s) need review."
            )

            for issue in issues:
                st.write(
                    f"- {issue}"
                )

            if st.button(
                "Return to Review",
                use_container_width=False,
            ):
                st.session_state.workspace = "Review"
                st.rerun()

        else:

            st.success(
                "Quiz validation passed. "
                "No blocking issues were found."
            )

            st.metric(
                "Validated Questions",
                len(questions),
            )

            if st.button(
                "Continue to Export",
                type="primary",
            ):
                st.session_state.workspace = "Export"
                st.rerun()


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.workspace == "Export":

    if "quiz_data" not in st.session_state:

        st.warning(
            "Analyze a document before exporting."
        )

    else:

        quiz = st.session_state[
            "quiz_data"
        ]

        questions = quiz[
            "questions"
        ]

        st.markdown(
            '<div class="cc-eyebrow">Export</div>',
            unsafe_allow_html=True,
        )

        st.title(
            "Canvas Export"
        )

        st.markdown(
            """
            <div class="cc-subtitle">
                Generate a QTI package for import into
                your Canvas DEV shell.
            </div>
            """,
            unsafe_allow_html=True,
        )

        total_points = sum(
            question_points(
                question
            )
            for question in questions
        )

        metric1, metric2 = st.columns(
            2
        )

        metric1.metric(
            "Questions",
            len(questions),
        )

        metric2.metric(
            "Total Points",
            total_points,
        )

        st.markdown(
            """
            <div class="cc-panel">
                <div style="
                    font-weight:700;
                    font-size:1.05rem;
                    margin-bottom:0.5rem;
                ">
                    Canvas New Quiz package
                </div>

                <div class="cc-help">
                    Generate the QTI ZIP after reviewing
                    and validating the quiz. Import the
                    downloaded package into a Canvas DEV
                    shell before instructional use.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Generate Canvas Quiz",
            type="primary",
        ):

            try:

                with st.spinner(
                    "Building Canvas package..."
                ):

                    safe_title = (
                        quiz["title"]
                        .replace(
                            " ",
                            "_",
                        )
                        .replace(
                            "/",
                            "_",
                        )
                    )

                    output_file = (
                        f"{safe_title}_QTI.zip"
                    )

                    create_qti_package(
                        quiz,
                        output_file,
                    )

                    # Validate the completed Canvas package
                    # before allowing it to be downloaded.
                    results, errors, warnings = validate_qti_package(
                        output_file,
                        expected_questions=len(
                            quiz["questions"]
                        ),
                    )

                    if errors:
                        raise ValueError(
                            "Canvas package validation failed:\n"
                            + "\n".join(errors)
                        )

                    st.session_state[
                        "qti_validation_results"
                    ] = results

                    st.session_state[
                        "qti_validation_warnings"
                    ] = warnings

                    with open(
                        output_file,
                        "rb",
                    ) as file:

                        st.session_state[
                            "qti_zip"
                        ] = file.read()

                    st.session_state[
                        "qti_filename"
                    ] = output_file

                    if os.path.exists(
                        output_file
                    ):
                        os.remove(
                            output_file
                        )

                st.success(
                    "Canvas package created and validated successfully."
                )

            except Exception as error:

                st.error(
                    "CourseCraft could not create "
                    "the Canvas package."
                )

                st.exception(
                    error
                )

        if "qti_zip" in st.session_state:

            st.download_button(
                "Download Canvas Quiz",
                data=st.session_state[
                    "qti_zip"
                ],
                file_name=st.session_state[
                    "qti_filename"
                ],
                mime="application/zip",
                type="primary",
            )

            st.caption(
                "Canvas DEV → Settings → "
                "Import Course Content → QTI .zip file"
            )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    '<div class="cc-divider"></div>',
    unsafe_allow_html=True,
)

st.caption(
    "CourseCraft prepares Canvas resources for "
    "review and testing in a DEV shell before use "
    "in an instructional course."
)