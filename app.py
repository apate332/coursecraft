import json
import os
import tempfile

import streamlit as st

from ai.client import ask_asu_ai
from document.chunker import chunk_document
from document.extractor import extract_docx
from quiz.normalizer import normalize_quiz
from qti.package import create_qti_package
from qti.validator import validate_qti_package

PROMPT_PATH = "prompts/quiz_converter.txt"

st.set_page_config(
    page_title="CourseCraft",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "workspace" not in st.session_state:
    st.session_state.workspace = "Create"
if "selected_question" not in st.session_state:
    st.session_state.selected_question = 0

# -----------------------------------------------------------------------------
# Pastel design system
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --cc-ink: #2f2a35;
        --cc-muted: #746d7a;
        --cc-bg: #fffaf7;
        --cc-card: #ffffff;
        --cc-pink: #f7dce7;
        --cc-pink-strong: #d96f9d;
        --cc-blue: #dcecfb;
        --cc-blue-strong: #5d8fb8;
        --cc-yellow: #fff0bd;
        --cc-yellow-strong: #b88a24;
        --cc-lilac: #ebe3f7;
        --cc-green: #dff1e4;
        --cc-border: #e9e0e5;
    }

    .stApp { background: var(--cc-bg); color: var(--cc-ink); }
    header[data-testid="stHeader"] { background: rgba(255,250,247,.94); }
    section[data-testid="stSidebar"] { display: none; }

    .block-container {
        max-width: 1500px;
        padding-top: 3.5rem !important;
        padding-bottom: 4rem !important;
        padding-left: 3.5rem !important;
        padding-right: 3.5rem !important;
    }

    h1, h2, h3 { color: var(--cc-ink); letter-spacing: -0.025em; }
    h1 { font-size: 2.35rem !important; font-weight: 760 !important; }
    h2 { font-size: 1.45rem !important; font-weight: 720 !important; }
    h3 { font-size: 1.05rem !important; font-weight: 700 !important; }
    p, label, .stCaption { color: var(--cc-muted); }

    div.stButton > button, div.stDownloadButton > button {
        min-height: 3rem !important;
        height: auto !important;
        padding: 0.7rem 1rem !important;
        line-height: 1.2 !important;
        order-radius: 12px !important;
        font-weight: 650 !important;
    }
    div.stButton > button p,
    div.stDownloadButton > button p {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.25 !important;
        overflow: visible !important;
    }
    div.stButton > button > div,
    div.stDownloadButton > button > div {
        overflow: visible !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        border-color: #cdbfc7;
        color: var(--cc-ink);
    }
    /* =====================================================
       PRIMARY ACTION BUTTONS
       ===================================================== */

    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background-color: #d66b9a !important;
        border: 1px solid #d66b9a !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Force Streamlit's inner text to white */
    div.stButton > button[kind="primary"] *,
    div.stDownloadButton > button[kind="primary"] * {
        color: #ffffff !important;
    }

    /* Hover */
    div.stButton > button[kind="primary"]:hover,
    div.stDownloadButton > button[kind="primary"]:hover {
        background-color: #c85b8c !important;
        border-color: #c85b8c !important;
        color: #ffffff !important;
    }

    div.stButton > button[kind="primary"]:hover *,
    div.stDownloadButton > button[kind="primary"]:hover * {
        color: #ffffff !important;
    }

    /* Active / clicked */
    div.stButton > button[kind="primary"]:active,
    div.stDownloadButton > button[kind="primary"]:active {
        background-color: #b94f7d !important;
        border-color: #b94f7d !important;
        color: #ffffff !important;
    }
    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid var(--cc-border);
        border-radius: 16px;
        padding: 1rem 1.1rem;
    }
    div[data-testid="stMetricLabel"] { color: var(--cc-muted); }
    div[data-testid="stMetricValue"] { color: var(--cc-ink); }

    section[data-testid="stFileUploaderDropzone"] {
        background: #fff;
        border: 2px dashed #d9c7d0;
        border-radius: 20px;
        padding: 2.1rem 1.4rem;
    }
    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--cc-pink-strong);
        background: #fffdfd;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        border-radius: 12px;
        border-color: var(--cc-border);
        background: #fff;
    }

    div[data-testid="stAlert"] { border-radius: 14px; }
    div[data-testid="stStatusWidget"] { border-radius: 16px; }

    .cc-brand {
        font-size: 1.45rem;
        font-weight: 800;
        color: var(--cc-ink);
        letter-spacing: -0.03em;
        padding-top: .35rem;
    }
    .cc-kicker {
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
        color: var(--cc-pink-strong);
        margin-bottom: .35rem;
    }
    .cc-subtitle {
        font-size: 1.03rem;
        color: var(--cc-muted);
        max-width: 720px;
        margin-top: -.35rem;
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }
    .cc-card {
        background: #fff;
        border: 1px solid var(--cc-border);
        border-radius: 18px;
        padding: 1.25rem 1.35rem;
        margin: .6rem 0 1rem;
    }
    .cc-pink { background: var(--cc-pink); }
    .cc-blue { background: var(--cc-blue); }
    .cc-yellow { background: var(--cc-yellow); }
    .cc-green { background: var(--cc-green); }
    .cc-lilac { background: var(--cc-lilac); }
    .cc-card-title { font-weight: 760; color: var(--cc-ink); margin-bottom: .25rem; }
    .cc-small { color: var(--cc-muted); font-size: .9rem; line-height: 1.5; }
    .cc-pill {
        display: inline-block;
        padding: .35rem .7rem;
        border-radius: 999px;
        background: var(--cc-blue);
        color: #416c8f;
        font-size: .78rem;
        font-weight: 760;
    }
    .cc-step {
        border-radius: 14px;
        padding: .75rem .85rem;
        text-align: center;
        font-weight: 700;
        font-size: .9rem;
        border: 1px solid var(--cc-border);
        background: #fff;
        color: var(--cc-muted);
    }
    .cc-step-active {
        background: var(--cc-blue);
        color: #416c8f;
        border-color: #c6dff4;
    }
    .cc-divider { height: 1px; background: var(--cc-border); margin: 1.4rem 0; }

    @media (max-width: 700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        h1 { font-size: 1.9rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def pretty_type(question_type):
    return {
        "multiple_choice": "Multiple Choice",
        "multiple_answer": "Multiple Answer",
        "numeric": "Numeric",
    }.get(question_type, (question_type or "Question").replace("_", " ").title())


def question_points(question):
    if question.get("zero_point"):
        return 0
    points = question.get("points")
    return 1 if points is None else points


def reset_quiz():
    for key in [
        "quiz_data",
        "qti_zip",
        "qti_filename",
        "qti_validation_results",
        "qti_validation_warnings",
    ]:
        st.session_state.pop(key, None)
    st.session_state.selected_question = 0
    st.session_state.workspace = "Create"


def reconcile_answer_flags(question):
    """Use explicit correct_answers text when AI choice flags conflict."""
    choices = question.get("choices") or []
    correct_answers = question.get("correct_answers") or []
    if not choices or not correct_answers:
        return question

    normalized_answers = {
        str(answer).strip().casefold() for answer in correct_answers if answer is not None
    }
    matched = 0
    for choice in choices:
        text = str(choice.get("text", "")).strip().casefold()
        is_correct = text in normalized_answers
        choice["correct"] = is_correct
        matched += int(is_correct)

    if matched:
        question["_answer_flags_reconciled"] = True
    return question


def prepare_quiz(quiz_data):
    for question in quiz_data.get("questions", []):
        reconcile_answer_flags(question)
    return normalize_quiz(quiz_data)


def quiz_issues(questions):
    issues = []
    for question in questions:
        number = question.get("number")
        qtype = question.get("type")
        if not str(question.get("prompt") or "").strip():
            issues.append((number, "Question text is missing."))
            continue

        if qtype in {"multiple_choice", "multiple_answer"}:
            choices = question.get("choices") or []
            correct_count = sum(bool(choice.get("correct")) for choice in choices)
            if not choices:
                issues.append((number, "No answer choices were found."))
            elif qtype == "multiple_choice" and correct_count != 1:
                issues.append((number, "Multiple Choice needs exactly one correct answer."))
            elif qtype == "multiple_answer" and correct_count < 1:
                issues.append((number, "Multiple Answer needs at least one correct answer."))
        elif qtype == "numeric" and question.get("numeric_answer") is None:
            issues.append((number, "Numeric answer is missing."))
    return issues


def go_to(name):
    st.session_state.workspace = name
    st.rerun()


# -----------------------------------------------------------------------------
# Top navigation
# -----------------------------------------------------------------------------
brand_col, new_col, review_col, validate_col, export_col = st.columns([2.5, 1, 1, 1, 1])
with brand_col:
    st.markdown('<div class="cc-brand">CourseCraft</div>', unsafe_allow_html=True)
with new_col:
    if st.button("New Quiz", use_container_width=True):
        reset_quiz()
        st.rerun()
with review_col:
    if st.button("Review", use_container_width=True, disabled="quiz_data" not in st.session_state):
        go_to("Review")
with validate_col:
    if st.button("Validate", use_container_width=True, disabled="quiz_data" not in st.session_state):
        go_to("Validate")
with export_col:
    if st.button("Export", use_container_width=True, disabled="quiz_data" not in st.session_state):
        go_to("Export")

step_names = ["Create", "Review", "Validate", "Export"]
step_cols = st.columns(4)
for idx, name in enumerate(step_names, start=1):
    active = st.session_state.workspace == name
    cls = "cc-step cc-step-active" if active else "cc-step"
    step_cols[idx - 1].markdown(
        f'<div class="{cls}">{idx}&nbsp;&nbsp;{name}</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="cc-divider"></div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Create
# -----------------------------------------------------------------------------
if st.session_state.workspace == "Create":
    st.markdown('<div class="cc-kicker">Start a new quiz</div>', unsafe_allow_html=True)
    st.title("Create a Canvas Quiz")
    st.markdown(
        '<div class="cc-subtitle">Upload a Word document and CourseCraft will identify the quiz questions, prepare them for review, and build a Canvas New Quiz package.</div>',
        unsafe_allow_html=True,
    )

    info1, info2, info3 = st.columns(3)
    info1.markdown('<div class="cc-card cc-blue"><div class="cc-card-title">1. Upload</div><div class="cc-small">Choose your curriculum or assignment document.</div></div>', unsafe_allow_html=True)
    info2.markdown('<div class="cc-card cc-pink"><div class="cc-card-title">2. Review</div><div class="cc-small">Check questions, answers, points, and feedback.</div></div>', unsafe_allow_html=True)
    info3.markdown('<div class="cc-card cc-yellow"><div class="cc-card-title">3. Export</div><div class="cc-small">Validate and download a Canvas-ready QTI package.</div></div>', unsafe_allow_html=True)

    st.subheader("Upload your curriculum")
    st.caption("Word documents (.docx) are supported in this version.")
    uploaded_file = st.file_uploader(
        "Upload Word document",
        type=["docx"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        size_mb = uploaded_file.size / (1024 * 1024)
        file_col, action_col = st.columns([4, 1.4], vertical_alignment="center")
        with file_col:
            st.markdown(
                f'<div class="cc-card cc-lilac"><div class="cc-card-title">{uploaded_file.name}</div><div class="cc-small">{size_mb:.1f} MB · Ready to analyze</div></div>',
                unsafe_allow_html=True,
            )
        with action_col:
            analyze = st.button("Analyze Document", type="primary", use_container_width=True)

        if analyze:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
                temp_file.write(uploaded_file.getbuffer())
                temp_path = temp_file.name

            try:
                status = st.status("Preparing your quiz", expanded=True)
                status.write("Reading the Word document...")
                content = extract_docx(temp_path)
                chunks = chunk_document(content, max_chars=6000, overlap_chars=1200)
                status.write(f"Document prepared in {len(chunks)} sections.")

                with open(PROMPT_PATH, "r", encoding="utf-8") as file:
                    instructions = file.read()

                all_questions = {}
                progress = st.progress(0, text="Starting AI analysis...")

                for index, chunk in enumerate(chunks, start=1):
                    progress.progress(
                        index / len(chunks),
                        text=f"Analyzing section {index} of {len(chunks)}",
                    )
                    prompt = f"""
{instructions}

This is section {index} of {len(chunks)} from one larger curriculum document.
Extract quiz questions that are sufficiently represented in this section.
Sections overlap, so a question may also appear in another section.
Do not invent missing information.

SOURCE CURRICULUM
==============================
{chunk}
==============================
END SOURCE CURRICULUM
"""
                    response = ask_asu_ai(prompt)
                    chunk_data = json.loads(response["response"])
                    for question in chunk_data.get("questions", []):
                        number = question.get("number")
                        if number is not None:
                            all_questions[number] = question

                questions = [all_questions[number] for number in sorted(all_questions)]
                quiz_data = prepare_quiz(
                    {
                        "title": os.path.splitext(uploaded_file.name)[0],
                        "questions": questions,
                    }
                )
                st.session_state.quiz_data = quiz_data
                st.session_state.selected_question = 0
                st.session_state.pop("qti_zip", None)
                st.session_state.pop("qti_filename", None)
                status.update(label="Quiz ready for review", state="complete", expanded=False)
                go_to("Review")
            except Exception as error:
                st.error("CourseCraft could not finish analyzing this document.")
                st.caption("Your document was not exported. You can retry the analysis after checking the error below.")
                st.exception(error)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

# -----------------------------------------------------------------------------
# Review
# -----------------------------------------------------------------------------
elif st.session_state.workspace == "Review":
    if "quiz_data" not in st.session_state:
        st.warning("Upload and analyze a document first.")
    else:
        quiz = st.session_state.quiz_data
        questions = quiz.get("questions", [])
        total_points = sum(question_points(q) for q in questions)
        numeric_count = sum(q.get("type") == "numeric" for q in questions)
        auto_fixes = sum(bool(q.get("_normalization_changes")) or bool(q.get("_answer_flags_reconciled")) for q in questions)

        title_col, badge_col = st.columns([5, 1.4], vertical_alignment="center")
        with title_col:
            st.markdown('<div class="cc-kicker">Review</div>', unsafe_allow_html=True)
            st.title(quiz.get("title", "CourseCraft Quiz"))
            st.markdown('<div class="cc-subtitle">Review what students will see. Edit any question before validation and export.</div>', unsafe_allow_html=True)
        with badge_col:
            st.markdown('<span class="cc-pill">Ready for review</span>', unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Questions", len(questions))
        m2.metric("Points", f"{total_points:g}")
        m3.metric("Numeric", numeric_count)
        m4.metric("Auto-fixes", auto_fixes)

        if auto_fixes:
            st.info(f"CourseCraft corrected {auto_fixes} structural answer/type issue(s) before review.")

        left, right = st.columns([1, 2.35], gap="large")
        with left:
            st.subheader("Questions")
            st.caption("Choose a question to edit.")
            labels = []
            for q in questions:
                fixed = " · Fixed" if q.get("_normalization_changes") or q.get("_answer_flags_reconciled") else ""
                labels.append(f"{int(q.get('number', 0)):02d}  {pretty_type(q.get('type'))}{fixed}")
            selected = st.radio(
                "Question list",
                labels,
                index=min(st.session_state.selected_question, max(len(labels) - 1, 0)),
                label_visibility="collapsed",
            )
            st.session_state.selected_question = labels.index(selected)

        with right:
            question = questions[st.session_state.selected_question]
            number = question.get("number")
            qtype = question.get("type")

            st.markdown(
                f'<div class="cc-card cc-blue"><div class="cc-card-title">Question {number}</div><div class="cc-small">{pretty_type(qtype)}</div></div>',
                unsafe_allow_html=True,
            )

            question["prompt"] = st.text_area(
                "Question text",
                value=question.get("prompt", ""),
                height=120,
                key=f"prompt_{number}",
            )

            if qtype in {"multiple_choice", "multiple_answer"}:
                st.subheader("Answer choices")
                choices = question.get("choices") or []
                for index, choice in enumerate(choices):
                    choice_col, correct_col = st.columns([5, 1.25], vertical_alignment="bottom")
                    with choice_col:
                        choice["text"] = st.text_input(
                            f"Choice {index + 1}",
                            value=choice.get("text", ""),
                            key=f"choice_{number}_{index}",
                        )
                    with correct_col:
                        choice["correct"] = st.checkbox(
                            "Correct",
                            value=bool(choice.get("correct")),
                            key=f"correct_{number}_{index}",
                        )

            elif qtype == "numeric":
                st.subheader("Numeric answer")
                a_col, t_col = st.columns(2)
                with a_col:
                    question["numeric_answer"] = st.number_input(
                        "Correct answer",
                        value=float(question.get("numeric_answer") or 0),
                        key=f"numeric_answer_{number}",
                    )
                with t_col:
                    question["numeric_tolerance"] = st.number_input(
                        "Tolerance",
                        min_value=0.0,
                        value=float(question.get("numeric_tolerance") or 0),
                        key=f"numeric_tolerance_{number}",
                    )

            st.subheader("Question settings")
            p_col, type_col = st.columns(2)
            with p_col:
                points = st.number_input(
                    "Points",
                    min_value=0.0,
                    value=float(question_points(question)),
                    step=1.0,
                    key=f"points_{number}",
                )
                question["points"] = points
                question["zero_point"] = points == 0
            with type_col:
                st.text_input(
                    "Question type",
                    value=pretty_type(qtype),
                    disabled=True,
                    key=f"type_{number}",
                )

            feedback_value = question.get("feedback")
            if isinstance(feedback_value, dict):
                feedback_value = feedback_value.get("general") or feedback_value.get("correct") or ""
            question["feedback"] = st.text_area(
                "Feedback",
                value=feedback_value or "",
                height=120,
                key=f"feedback_{number}",
            )

        st.markdown('<div class="cc-divider"></div>', unsafe_allow_html=True)
        back_col, next_col = st.columns([1, 1])
        with back_col:
            if st.button("Start Over", use_container_width=True):
                reset_quiz()
                st.rerun()
        with next_col:
            if st.button("Validate Quiz", type="primary", use_container_width=True):
                go_to("Validate")

# -----------------------------------------------------------------------------
# Validate
# -----------------------------------------------------------------------------
elif st.session_state.workspace == "Validate":
    if "quiz_data" not in st.session_state:
        st.warning("Upload and analyze a document first.")
    else:
        quiz = st.session_state.quiz_data
        questions = quiz.get("questions", [])
        issues = quiz_issues(questions)

        st.markdown('<div class="cc-kicker">Quality check</div>', unsafe_allow_html=True)
        st.title("Quiz Validation")
        st.markdown('<div class="cc-subtitle">CourseCraft checks question structure and answer data before building the Canvas package.</div>', unsafe_allow_html=True)

        if issues:
            st.markdown(
                f'<div class="cc-card cc-yellow"><div class="cc-card-title">{len(issues)} item(s) need attention</div><div class="cc-small">Fix these before exporting to Canvas.</div></div>',
                unsafe_allow_html=True,
            )
            for number, message in issues:
                row1, row2 = st.columns([5, 1])
                row1.warning(f"Question {number}: {message}")
                with row2:
                    if st.button("Review", key=f"review_issue_{number}", use_container_width=True):
                        matches = [i for i, q in enumerate(questions) if q.get("number") == number]
                        if matches:
                            st.session_state.selected_question = matches[0]
                        go_to("Review")
        else:
            st.markdown('<div class="cc-card cc-green"><div class="cc-card-title">Ready for Canvas</div><div class="cc-small">All questions passed the pre-export checks.</div></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Questions checked", len(questions))
            c2.metric("Blocking issues", 0)
            c3.metric("Numeric questions", sum(q.get("type") == "numeric" for q in questions))

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Back to Review", use_container_width=True):
                go_to("Review")
        with b2:
            if st.button("Continue to Export", type="primary", use_container_width=True, disabled=bool(issues)):
                go_to("Export")

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
elif st.session_state.workspace == "Export":
    if "quiz_data" not in st.session_state:
        st.warning("Upload and analyze a document first.")
    else:
        quiz = st.session_state.quiz_data
        questions = quiz.get("questions", [])
        total_points = sum(question_points(q) for q in questions)

        st.markdown('<div class="cc-kicker">Final step</div>', unsafe_allow_html=True)
        st.title("Canvas Export")
        st.markdown('<div class="cc-subtitle">Build and download the Canvas New Quiz package after review and validation.</div>', unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Questions", len(questions))
        m2.metric("Total points", f"{total_points:g}")
        m3.metric("Format", "New Quiz")

        st.markdown(
            f'<div class="cc-card cc-pink"><div class="cc-card-title">{quiz.get("title", "CourseCraft Quiz")}</div><div class="cc-small">Canvas New Quiz · {len(questions)} questions · {total_points:g} points</div></div>',
            unsafe_allow_html=True,
        )

        if st.button("Generate Canvas Quiz", type="primary", use_container_width=True):
            output_file = None
            try:
                with st.spinner("Building and validating the Canvas package..."):
                    safe_title = quiz.get("title", "CourseCraft_Quiz").replace(" ", "_").replace("/", "_")
                    output_file = f"{safe_title}_QTI.zip"
                    create_qti_package(quiz, output_file)
                    results, errors, warnings = validate_qti_package(
                        output_file,
                        expected_questions=len(questions),
                    )
                    if errors:
                        raise ValueError("Canvas package validation failed:\n" + "\n".join(errors))
                    with open(output_file, "rb") as file:
                        st.session_state.qti_zip = file.read()
                    st.session_state.qti_filename = output_file
                    st.session_state.qti_validation_results = results
                    st.session_state.qti_validation_warnings = warnings
                st.success("Canvas package created and validated successfully.")
            except Exception as error:
                st.error("CourseCraft could not create the Canvas package.")
                st.exception(error)
            finally:
                if output_file and os.path.exists(output_file):
                    os.remove(output_file)

        if "qti_zip" in st.session_state:
            st.markdown('<div class="cc-card cc-green"><div class="cc-card-title">Your Canvas quiz is ready</div><div class="cc-small">The package passed CourseCraft validation and is ready for your DEV shell.</div></div>', unsafe_allow_html=True)
            st.download_button(
                "Download Canvas Quiz",
                data=st.session_state.qti_zip,
                file_name=st.session_state.qti_filename,
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
            st.caption("Import into Canvas DEV: Settings → Import Course Content → QTI .zip file")

        if st.button("Back to Review", use_container_width=False):
            go_to("Review")

st.markdown('<div class="cc-divider"></div>', unsafe_allow_html=True)
st.caption("CourseCraft · Review and test generated Canvas resources in a DEV shell before instructional use.")
