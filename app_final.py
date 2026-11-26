import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta

# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="SmartStudy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. CONSTANTS
# =========================================================

APP_DATA_FILE = "app_data.json"
PROGRESS_FILE = "study_progress.json"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:1b"

# =========================================================
# 3. JSON STORAGE FUNCTIONS
# =========================================================

def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except Exception as error:
        st.error(f"Unable to save data: {error}")


def load_app_data():
    return load_json(APP_DATA_FILE)


def save_app_data(data):
    save_json(APP_DATA_FILE, data)


def load_progress():
    return load_json(PROGRESS_FILE)


def save_progress(data):
    save_json(PROGRESS_FILE, data)


# =========================================================
# 4. INITIALIZE SESSION STATE
# =========================================================

if "app_data_loaded" not in st.session_state:
    saved_data = load_app_data()

    st.session_state.student_name = saved_data.get("name", "")
    st.session_state.subject_count = saved_data.get("subject_count", 3)
    st.session_state.study_hours = saved_data.get("hours", 4)
    st.session_state.study_difficulty = saved_data.get(
        "difficulty", "Medium"
    )

    saved_subjects = saved_data.get("subjects", [])
    saved_dates = saved_data.get("exam_dates", {})

    for i in range(10):
        subject_key = f"subject_name_{i}"
        date_key = f"subject_date_{i}"

        if subject_key not in st.session_state:
            st.session_state[subject_key] = (
                saved_subjects[i] if i < len(saved_subjects) else ""
            )

        if date_key not in st.session_state:
            try:
                stored_date = saved_dates.get(str(i))
                st.session_state[date_key] = (
                    date.fromisoformat(stored_date)
                    if stored_date else date.today() + timedelta(days=30)
                )
            except (ValueError, TypeError):
                st.session_state[date_key] = (
                    date.today() + timedelta(days=30)
                )

    st.session_state.app_data_loaded = True


# =========================================================
# 5. CUSTOM CSS
# =========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #f5f8ff;
    }

    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #173b70;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 16px;
        color: #64748b;
        margin-bottom: 25px;
    }

    .section-title {
        color: #173b70;
        font-weight: 700;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e2e8f0;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
        min-height: 42px;
    }

    div[data-testid="stExpander"] {
        background-color: white;
        border-radius: 10px;
    }

    .footer {
        text-align: center;
        color: #64748b;
        padding: 25px;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 6. HELPER FUNCTIONS
# =========================================================

def get_subjects():
    subjects = []

    for i in range(st.session_state.subject_count):
        name = st.session_state.get(
            f"subject_name_{i}", ""
        ).strip()

        exam_date = st.session_state.get(
            f"subject_date_{i}", date.today()
        )

        if name:
            subjects.append({
                "name": name,
                "exam_date": exam_date
            })

    return subjects


def save_current_app_data(subjects):
    names = [subject["name"] for subject in subjects]

    exam_dates = {}

    for i in range(st.session_state.subject_count):
        exam_date = st.session_state.get(f"subject_date_{i}")
        if exam_date:
            exam_dates[str(i)] = exam_date.isoformat()

    data = {
        "name": st.session_state.student_name,
        "subject_count": st.session_state.subject_count,
        "subjects": names,
        "hours": st.session_state.study_hours,
        "difficulty": st.session_state.study_difficulty,
        "exam_dates": exam_dates
    }

    save_app_data(data)


def generate_timetable(subjects, hours, difficulty):
    """Generate a seven-day timetable using Python scheduling rules."""

    if not subjects:
        return pd.DataFrame(), "Please add subjects first."

    sorted_subjects = sorted(
        subjects,
        key=lambda x: x["exam_date"]
    )

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    rows = []
    timetable_text = "SMARTSTUDY AI - 7 DAY STUDY PLAN\n\n"

    for day_number in range(7):
        current_date = monday + timedelta(days=day_number)

        subject = sorted_subjects[day_number % len(sorted_subjects)]
        subject_name = subject["name"]

        if hours == 1:
            study_time = 0.5
            revision_time = 0.5
        else:
            revision_time = 1.0
            study_time = hours - revision_time

        if difficulty == "Hard":
            main_time = study_time * 0.65
            practice_time = study_time * 0.35
        else:
            main_time = study_time * 0.60
            practice_time = study_time * 0.40

        plan = (
            f"Study {subject_name}: {main_time:.1f} hours | "
            f"Practice: {practice_time:.1f} hours | "
            f"Revision: {revision_time:.1f} hours"
        )

        rows.append({
            "Day": current_date.strftime("%A"),
            "Date": current_date.strftime("%d %b %Y"),
            "Subject": subject_name,
            "Study Hours": round(main_time, 1),
            "Practice Hours": round(practice_time, 1),
            "Revision Hours": round(revision_time, 1),
            "Total Hours": round(hours, 1)
        })

        timetable_text += (
            f"{current_date.strftime('%A, %d %B %Y')}\n"
            f"{plan}\n\n"
        )

    return pd.DataFrame(rows), timetable_text


def get_ai_advice(subjects, hours, difficulty):
    """Get study advice from the local Ollama model."""

    subject_names = ", ".join(
        subject["name"] for subject in subjects
    )

    prompt = f"""
    You are an experienced academic study planner.

    Student subjects: {subject_names}
    Daily available study hours: {hours}
    Difficulty level: {difficulty}

    Give the student:
    1. One practical study strategy.
    2. One time-management suggestion.
    3. One motivational suggestion.

    Keep your response concise and easy to understand.
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful AI study assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.3,
                    "num_predict": 120,
                    "num_ctx": 1024
                }
            },
            timeout=90
        )

        response.raise_for_status()
        result = response.json()

        return result.get("message", {}).get(
            "content",
            "No advice was returned by the AI model."
        )

    except requests.exceptions.ConnectionError:
        return (
            "Ollama is not running. Open Ollama on your computer "
            "and try again."
        )

    except requests.exceptions.Timeout:
        return (
            "The AI model is taking too long to respond. "
            "Please try again."
        )

    except Exception as error:
        return f"Unable to get AI advice: {error}"


# =========================================================
# 7. STUDY PROGRESS TRACKER
# =========================================================

def display_progress_tracker(subjects):

    st.markdown(
        '<h2 class="section-title">📊 Study Progress Tracker</h2>',
        unsafe_allow_html=True
    )

    st.write(
        "Add topics for each subject and mark completed topics "
        "to monitor your learning progress."
    )

    if not subjects:
        st.info("Please add subjects on the Dashboard first.")
        return

    progress_data = load_progress()

    total_topics_all = 0
    completed_all = 0

    for subject_index, subject in enumerate(subjects):

        subject_name = subject["name"]

        with st.container(border=True):

            st.subheader(f"📚 {subject_name}")

            saved_subject = progress_data.get(subject_name, {})

            saved_topics = saved_subject.get("topics", [])
            saved_completed = saved_subject.get("completed", [])

            topics_key = f"topics_{subject_index}"

            if topics_key not in st.session_state:
                st.session_state[topics_key] = "\n".join(saved_topics)

            topics_text = st.text_area(
                f"Enter topics for {subject_name} "
                "(one topic per line)",
                key=topics_key,
                height=100
            )

            topics = [
                topic.strip()
                for topic in topics_text.splitlines()
                if topic.strip()
            ]

            completed_topics = []

            for topic_index, topic in enumerate(topics):

                checkbox_key = (
                    f"completed_{subject_index}_{topic_index}_{topic}"
                )

                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = (
                        topic in saved_completed
                    )

                is_completed = st.checkbox(
                    topic,
                    key=checkbox_key
                )

                if is_completed:
                    completed_topics.append(topic)

            total_topics = len(topics)
            completed_count = len(completed_topics)

            total_topics_all += total_topics
            completed_all += completed_count

            percentage = (
                completed_count / total_topics * 100
                if total_topics > 0 else 0
            )

            st.progress(int(percentage))

            st.caption(
                f"{completed_count} of {total_topics} topics completed "
                f"({percentage:.1f}%)"
            )

            progress_data[subject_name] = {
                "topics": topics,
                "completed": completed_topics
            }

    save_progress(progress_data)

    st.divider()

    overall_percentage = (
        completed_all / total_topics_all * 100
        if total_topics_all > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Topics", total_topics_all)
    col2.metric("Completed Topics", completed_all)
    col3.metric("Overall Progress", f"{overall_percentage:.1f}%")

    st.progress(int(overall_percentage))

    report = "SMARTSTUDY AI - PROGRESS REPORT\n\n"

    for subject_name, details in progress_data.items():

        report += f"Subject: {subject_name}\n"

        for topic in details.get("topics", []):
            status = (
                "Completed"
                if topic in details.get("completed", [])
                else "Pending"
            )
            report += f"- {topic}: {status}\n"

        report += "\n"

    st.download_button(
        "⬇️ Download Progress Report",
        data=report,
        file_name="study_progress_report.txt",
        mime="text/plain"
    )


# =========================================================
# 8. SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:

    st.title("🎓 SmartStudy AI")

    st.caption("Your Personal AI Study Planner")

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "📊 Study Progress",
            "ℹ️ About Project"
        ]
    )

    st.divider()

    st.caption("Powered by Streamlit, Python and Ollama")


# =========================================================
# 9. ABOUT PROJECT PAGE
# =========================================================

if page == "ℹ️ About Project":

    st.title("ℹ️ About SmartStudy AI")

    st.write(
        "SmartStudy AI is a personal study planning application "
        "designed to help students organise their academic preparation."
    )

    st.subheader("🎯 Project Objectives")

    st.markdown("""
    - Organise subjects and examination dates.
    - Calculate remaining days before examinations.
    - Generate a seven-day study timetable.
    - Provide personalised study advice using a local AI model.
    - Track completed and pending topics.
    - Save student information and progress.
    """)

    st.subheader("🛠️ Technologies Used")

    st.markdown("""
    | Technology | Purpose |
    |---|---|
    | Python | Main programming language |
    | Streamlit | User interface |
    | Ollama | Local AI model platform |
    | Llama 3.2 | Generates study advice |
    | Pandas | Tabular data handling |
    | Plotly | Interactive visualisations |
    | JSON | Data storage |
    """)

    st.subheader("⚙️ How It Works")

    st.write(
        "The application accepts student information, processes "
        "exam dates, creates a timetable using Python logic, "
        "requests AI-generated advice from Ollama and stores "
        "study progress in JSON files."
    )

    st.info(
        "SmartStudy AI aims to make studying more organised, "
        "structured and manageable."
    )

    st.stop()


# =========================================================
# 10. GET SUBJECTS
# =========================================================

subjects = get_subjects()


# =========================================================
# 11. STUDY PROGRESS PAGE
# =========================================================

if page == "📊 Study Progress":

    st.title("📊 Your Study Progress")

    display_progress_tracker(subjects)

    st.markdown(
        '<div class="footer">SmartStudy AI | Study Smarter, Not Harder</div>',
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# 12. MAIN DASHBOARD
# =========================================================

st.markdown(
    '<div class="main-title">🎓 SmartStudy AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Your Personal AI-Powered Study Planner'
    '</div>',
    unsafe_allow_html=True
)

st.divider()

# Student information

st.subheader("👤 Student Information")

st.text_input(
    "Enter your name",
    key="student_name",
    placeholder="Your name"
)

st.subheader("📚 Subject and Examination Details")

st.caption(
    "Enter each subject and its individual examination date."
)

# Subject count

st.slider(
    "Number of subjects",
    min_value=1,
    max_value=10,
    key="subject_count"
)

# Subject fields

for i in range(st.session_state.subject_count):

    col1, col2 = st.columns(2)

    with col1:
        st.text_input(
            f"Subject {i + 1}",
            key=f"subject_name_{i}",
            placeholder=f"Enter subject {i + 1}"
        )

    with col2:
        st.date_input(
            f"Exam date for Subject {i + 1}",
            key=f"subject_date_{i}"
        )

# Study preferences

st.subheader("⏰ Study Preferences")

col1, col2 = st.columns(2)

with col1:
    st.slider(
        "Daily available study hours",
        min_value=1,
        max_value=12,
        key="study_hours"
    )

with col2:
    st.selectbox(
        "Subject difficulty level",
        ["Easy", "Medium", "Hard"],
        key="study_difficulty"
    )

# Save application details

subjects = get_subjects()
save_current_app_data(subjects)

st.divider()


# =========================================================
# 13. DASHBOARD ANALYTICS
# =========================================================

st.markdown(
    '<h2 class="section-title">📈 Study Overview</h2>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Subjects",
    len(subjects)
)

col2.metric(
    "Daily Study Hours",
    f"{st.session_state.study_hours} hrs"
)

col3.metric(
    "Difficulty Level",
    st.session_state.study_difficulty
)

if subjects:

    today = date.today()

    upcoming_exams = [
        subject for subject in subjects
        if subject["exam_date"] >= today
    ]

    if upcoming_exams:

        next_exam = min(
            upcoming_exams,
            key=lambda x: x["exam_date"]
        )

        days_remaining = (
            next_exam["exam_date"] - today
        ).days

        st.subheader("⏳ Next Examination")

        col1, col2 = st.columns(2)

        col1.metric(
            "Next Exam",
            next_exam["name"]
        )

        col2.metric(
            "Days Remaining",
            days_remaining
        )

    else:
        st.warning(
            "All entered examination dates are in the past."
        )

    # Exam schedule chart

    st.subheader("📅 Examination Schedule Analysis")

    chart_data = pd.DataFrame([
        {
            "Subject": subject["name"],
            "Exam Date": subject["exam_date"],
            "Days Remaining": (
                subject["exam_date"] - today
            ).days
        }
        for subject in subjects
    ])

    chart_data = chart_data.sort_values("Exam Date")

    fig = px.bar(
        chart_data,
        x="Subject",
        y="Days Remaining",
        color="Subject",
        title="Days Remaining for Each Examination",
        labels={
            "Days Remaining": "Days Until Exam",
            "Subject": "Subjects"
        },
        text="Days Remaining"
    )

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        height=400
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="exam_schedule_chart"
    )

else:

    st.info(
        "Add at least one subject to view your examination analytics."
    )


# =========================================================
# 14. SEVEN-DAY STUDY TIMETABLE
# =========================================================

st.divider()

st.markdown(
    '<h2 class="section-title">🗓️ Smart 7-Day Study Planner</h2>',
    unsafe_allow_html=True
)

st.write(
    "Generate a weekly study schedule based on your subjects, "
    "examination dates and available study hours."
)

if st.button(
    "✨ Generate My 7-Day Study Plan",
    use_container_width=True
):

    if not subjects:
        st.warning("Please enter at least one subject.")

    else:

        timetable_df, timetable_text = generate_timetable(
            subjects,
            st.session_state.study_hours,
            st.session_state.study_difficulty
        )

        st.session_state.timetable_df = timetable_df
        st.session_state.timetable_text = timetable_text

        st.success("Your seven-day study plan is ready!")


if "timetable_df" in st.session_state:

    st.subheader("📋 Your Weekly Timetable")

    st.dataframe(
        st.session_state.timetable_df,
        use_container_width=True,
        hide_index=True
    )

    with st.expander("📖 View Daily Study Details"):

        for _, row in st.session_state.timetable_df.iterrows():

            st.markdown(
                f"**{row['Day']} – {row['Date']}**"
            )

            st.write(
                f"Subject: {row['Subject']}"
            )

            st.write(
                f"Study: {row['Study Hours']} hours"
            )

            st.write(
                f"Practice: {row['Practice Hours']} hours"
            )

            st.write(
                f"Revision: {row['Revision Hours']} hours"
            )

            st.divider()

    st.download_button(
        "⬇️ Download 7-Day Study Plan",
        data=st.session_state.timetable_text,
        file_name="smartstudy_7_day_timetable.txt",
        mime="text/plain"
    )


# =========================================================
# 15. OLLAMA AI STUDY ADVICE
# =========================================================

st.divider()

st.markdown(
    '<h2 class="section-title">🤖 AI Study Assistant</h2>',
    unsafe_allow_html=True
)

st.write(
    "Get personalised study suggestions from your local "
    "Llama 3.2 AI model."
)

if st.button(
    "💡 Get AI Study Advice",
    use_container_width=True
):

    if not subjects:
        st.warning("Please add subjects before requesting AI advice.")

    else:

        with st.spinner(
            "AI is preparing your personalised study advice..."
        ):

            advice = get_ai_advice(
                subjects,
                st.session_state.study_hours,
                st.session_state.study_difficulty
            )

        st.session_state.ai_advice = advice


if "ai_advice" in st.session_state:

    st.markdown("### 🌟 Your Personalised Study Advice")

    st.info(st.session_state.ai_advice)


# =========================================================
# 16. DASHBOARD FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div class="footer">
        <b>SmartStudy AI</b><br>
        Study Smarter, Not Harder 🚀<br>
        Built using Python, Streamlit and Ollama
    </div>
    """,
    unsafe_allow_html=True
)