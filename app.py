
# ==============================================================
# SMARTSTUDY AI - PREMIUM EDITION
# Personal AI-Powered Study Planner
# ==============================================================

import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import plotly.express as px
import json
import os
import html
import calendar as pycalendar

from datetime import date, datetime, timedelta


# ==============================================================
# 1. PAGE CONFIGURATION
# ==============================================================

st.set_page_config(
    page_title="SmartStudy AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================================================
# 2. CONSTANTS
# ==============================================================

APP_DATA_FILE = "app_data.json"
PROGRESS_FILE = "study_progress.json"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:1b"

DEFAULT_TOPICS = [
    "Introduction and Fundamentals",
    "Important Concepts",
    "Practice Questions",
    "Previous Year Questions",
    "Revision"
]


# ==============================================================
# 3. PREMIUM CSS
# ==============================================================

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fc;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

h1, h2, h3 {
    color: #172554;
    font-weight: 750;
}

p, label {
    color: #334155;
}

 {
   [data-testid="stSidebar"] {
    background: #E0F2FE !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] div {
    color: #172554 !important;
}

[data-testid="stSidebar"] button {
    background-color: #2563EB !important;
    color: white !important;
    border: 1px solid #1D4ED8 !important;
    border-radius: 8px !important;
}

}

section[data-testid="stSidebar"] * {
   [data-testid="stSidebar"] {
    background: #241044 !important;
}

[data-testid="stSidebar"] > div {
    background: #241044 !important;
}

[data-testid="stSidebar"] * {
    color: #FFD166 !important;
}

[data-testid="stSidebar"] button {
    background: #6D28D9 !important;
    color: #FFFFFF !important;
    border: 2px solid #A78BFA !important;
    border-radius: 10px !important;
} 
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e2e8f0;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
}

div[data-testid="stMetricValue"] {
    color: #1e3a8a;
    font-weight: 750;
}

.stButton > button {
    background: linear-gradient(90deg, #2563eb, #6366f1);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 650;
    transition: 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #1d4ed8, #4f46e5);
    color: white;
    border: none;
}

.stDownloadButton > button {
    background: #eef2ff;
    color: #3730a3;
    border: 1px solid #c7d2fe;
    border-radius: 10px;
    font-weight: 650;
}

.custom-card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
    margin-bottom: 15px;
}

.hero {
    background: linear-gradient(
        120deg,
        #1e3a8a,
        #4338ca,
        #6366f1
    );
    padding: 30px;
    border-radius: 20px;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 34px;
}

.hero p {
    color: #e0e7ff;
    font-size: 16px;
}

.footer {
    text-align: center;
    color: #64748b;
    padding: 25px 0;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)


# ==============================================================
# 4. JSON FILE MANAGEMENT
# ==============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return default


def save_json(filename, data):

    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except OSError:
        st.error(
            f"Unable to save {filename}. "
            "Check your folder permissions."
        )
        return False


# ==============================================================
# 5. DATA NORMALIZATION
# Handles older JSON formats safely
# ==============================================================

def safe_exam_date(value):

    try:
        if isinstance(value, date):
            return value.isoformat()

        if value:
            return date.fromisoformat(str(value)[:10]).isoformat()

    except (ValueError, TypeError):
        pass

    return (date.today() + timedelta(days=15)).isoformat()


def normalize_subjects(raw_subjects):

    normalized = []

    if not isinstance(raw_subjects, list):
        return normalized

    for index, item in enumerate(raw_subjects):

        if isinstance(item, str):

            name = item.strip()

            if name:
                normalized.append({
                    "name": name,
                    "exam_date": safe_exam_date(None),
                    "difficulty": "Medium"
                })

        elif isinstance(item, dict):

            name = str(
                item.get("name", item.get("subject", ""))
            ).strip()

            if not name:
                continue

            difficulty = item.get(
                "difficulty",
                item.get("level", "Medium")
            )

            if difficulty not in ["Easy", "Medium", "Hard"]:
                difficulty = "Medium"

            normalized.append({
                "name": name,
                "exam_date": safe_exam_date(
                    item.get(
                        "exam_date",
                        item.get("date")
                    )
                ),
                "difficulty": difficulty
            })

    return normalized


def normalize_app_data(raw_data):

    if not isinstance(raw_data, dict):
        raw_data = {}

    # Support older student-name and hours field names.
    student_name = raw_data.get(
        "student_name",
        raw_data.get("name", "")
    )

    daily_hours = raw_data.get(
        "daily_hours",
        raw_data.get("hours", 4)
    )

    try:
        daily_hours = int(daily_hours)
    except (ValueError, TypeError):
        daily_hours = 4

    daily_hours = max(1, min(12, daily_hours))

    raw_subjects = raw_data.get(
        "subjects",
        raw_data.get("subject_list", [])
    )

    return {
        "student_name": str(student_name),
        "subjects": normalize_subjects(raw_subjects),
        "daily_hours": daily_hours,
        "created_at": raw_data.get(
            "created_at",
            str(date.today())
        )
    }


# ==============================================================
# 6. PROGRESS DATA NORMALIZATION
# ==============================================================

def normalize_progress(raw_progress, subjects):

    if not isinstance(raw_progress, dict):
        raw_progress = {}

    normalized = {}

    for subject in subjects:

        name = subject["name"]
        old_topics = raw_progress.get(name, [])

        if not isinstance(old_topics, list):
            old_topics = []

        topics = []

        for item in old_topics:

            if isinstance(item, str):

                topics.append({
                    "topic": item,
                    "completed": False
                })

            elif isinstance(item, dict):

                topic_name = str(
                    item.get(
                        "topic",
                        item.get("name", "")
                    )
                ).strip()

                if topic_name:
                    topics.append({
                        "topic": topic_name,
                        "completed": bool(
                            item.get(
                                "completed",
                                item.get("done", False)
                            )
                        )
                    })

        if not topics:
            topics = [
                {
                    "topic": topic,
                    "completed": False
                }
                for topic in DEFAULT_TOPICS
            ]

        normalized[name] = topics

    return normalized


# ==============================================================
# 7. INITIALIZE SESSION STATE
# ==============================================================

if "app_data" not in st.session_state:

    raw_data = load_json(
        APP_DATA_FILE,
        {}
    )

    st.session_state.app_data = normalize_app_data(
        raw_data
    )

    # Save converted data in the new consistent format.
    save_json(
        APP_DATA_FILE,
        st.session_state.app_data
    )


if "study_progress" not in st.session_state:

    raw_progress = load_json(
        PROGRESS_FILE,
        {}
    )

    st.session_state.study_progress = normalize_progress(
        raw_progress,
        st.session_state.app_data["subjects"]
    )

    save_json(
        PROGRESS_FILE,
        st.session_state.study_progress
    )


if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


if "ai_advice" not in st.session_state:
    st.session_state.ai_advice = None


if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = date.today().year


if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = date.today().month


# ==============================================================
# 8. HELPER FUNCTIONS
# ==============================================================

def get_subjects():
    return st.session_state.app_data["subjects"]


def save_current_app_data():
    return save_json(
        APP_DATA_FILE,
        st.session_state.app_data
    )


def get_exam_days(exam_date):

    try:
        exam = date.fromisoformat(str(exam_date))
        return (exam - date.today()).days

    except (ValueError, TypeError):
        return None


def get_exam_status(days):

    if days is None:
        return "Date unavailable"

    if days < 0:
        return "Exam completed"

    if days == 0:
        return "Exam today"

    if days <= 7:
        return "Urgent"

    if days <= 30:
        return "Upcoming"

    return "On track"


def get_progress_percentage(subject_name):

    topics = st.session_state.study_progress.get(
        subject_name,
        []
    )

    if not topics:
        return 0

    completed = sum(
        1
        for topic in topics
        if topic.get("completed", False)
    )

    return round(
        completed / len(topics) * 100,
        1
    )


def get_all_progress():

    subjects = get_subjects()

    if not subjects:
        return 0

    values = [
        get_progress_percentage(subject["name"])
        for subject in subjects
    ]

    return round(sum(values) / len(values), 1)


def initialize_progress():

    old_progress = st.session_state.study_progress

    st.session_state.study_progress = normalize_progress(
        old_progress,
        get_subjects()
    )

    save_json(
        PROGRESS_FILE,
        st.session_state.study_progress
    )


# ==============================================================
# 9. TIMETABLE GENERATION
# ==============================================================

def generate_timetable(subjects, daily_hours):

    if not subjects:
        return pd.DataFrame()

    sorted_subjects = sorted(
        subjects,
        key=lambda item: item["exam_date"]
    )

    timetable = []

    today = date.today()

    monday = today - timedelta(days=today.weekday())

    for day_number in range(7):

        current_day = monday + timedelta(days=day_number)

        subject = sorted_subjects[
            day_number % len(sorted_subjects)
        ]

        difficulty = subject["difficulty"]

        if daily_hours == 1:

            study_time = 0.5
            practice_time = 0
            revision_time = 0.5

        else:

            revision_time = 1
            remaining_time = daily_hours - revision_time

            if difficulty == "Hard":

                study_time = round(
                    remaining_time * 0.65, 2
                )

                practice_time = round(
                    remaining_time * 0.35, 2
                )

            else:

                study_time = round(
                    remaining_time * 0.60, 2
                )

                practice_time = round(
                    remaining_time * 0.40, 2
                )

        timetable.append({

            "Date": current_day.strftime("%d %b %Y"),

            "Day": current_day.strftime("%A"),

            "Subject": subject["name"],

            "Difficulty": difficulty,

            "Study (hrs)": study_time,

            "Practice (hrs)": practice_time,

            "Revision (hrs)": revision_time,

            "Total (hrs)": round(
                study_time + practice_time + revision_time,
                2
            )
        })

    return pd.DataFrame(timetable)


# ==============================================================
# 10. OLLAMA AI STUDY ASSISTANT
# ==============================================================

def get_ai_advice(student_name, subjects, daily_hours):

    subject_details = "\n".join([
        (
            f"- {subject['name']}: "
            f"Exam date: {subject['exam_date']}, "
            f"Difficulty: {subject['difficulty']}"
        )
        for subject in subjects
    ])

    prompt = f"""
You are SmartStudy AI, a helpful academic study assistant.

Student: {student_name}
Daily available study hours: {daily_hours}

Subjects:
{subject_details}

Today's date: {date.today()}

Provide personalized guidance with:

1. Most urgent subject and reason.
2. A practical study strategy.
3. Time management advice.
4. Revision technique.
5. Motivational message.

Use headings and bullet points.
Be concise, realistic and encouraging.
Do not invent examination dates.
"""

    payload = {

        "model": OLLAMA_MODEL,

        "messages": [

            {
                "role": "system",
                "content": (
                    "You are a knowledgeable and supportive "
                    "academic study assistant."
                )
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
            "num_predict": 250,
            "num_ctx": 1024
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        return result.get(
            "message", {}
        ).get(
            "content",
            "AI did not return a response."
        )

    except requests.exceptions.ConnectionError:

        return (
            "Cannot connect to Ollama. "
            "Please make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        return (
            "AI response took too long. "
            "Please try again."
        )

    except requests.exceptions.RequestException as error:

        return f"AI service error: {error}"

    except (ValueError, KeyError):

        return "Unable to process the AI response."


# ==============================================================
# 11. EXAM CALENDAR
# ==============================================================

def display_exam_calendar(subjects):

    st.subheader("📅 Monthly Examination Calendar")

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:

        if st.button("◀ Previous", key="cal_previous"):

            if st.session_state.calendar_month == 1:

                st.session_state.calendar_month = 12
                st.session_state.calendar_year -= 1

            else:

                st.session_state.calendar_month -= 1

            st.rerun()

    with col2:

        month_name = pycalendar.month_name[
            st.session_state.calendar_month
        ]

        st.markdown(
            f"<h3 style='text-align:center;'>"
            f"{month_name} {st.session_state.calendar_year}"
            f"</h3>",
            unsafe_allow_html=True
        )

    with col3:

        if st.button("Next ▶", key="cal_next"):

            if st.session_state.calendar_month == 12:

                st.session_state.calendar_month = 1
                st.session_state.calendar_year += 1

            else:

                st.session_state.calendar_month += 1

            st.rerun()

    exam_dates = {}

    for subject in subjects:

        exam_day = date.fromisoformat(
            subject["exam_date"]
        )

        if exam_day not in exam_dates:
            exam_dates[exam_day] = []

        exam_dates[exam_day].append(subject["name"])

    weeks = pycalendar.monthcalendar(
        st.session_state.calendar_year,
        st.session_state.calendar_month
    )

    headers = [
        "Mon", "Tue", "Wed", "Thu",
        "Fri", "Sat", "Sun"
    ]

    calendar_html = """
    <style>
    .exam-calendar {
        width: 100%;
        border-collapse: separate;
        border-spacing: 5px;
        table-layout: fixed;
    }

    .exam-calendar th {
        background: #e0e7ff;
        color: #312e81;
        padding: 12px 2px;
        border-radius: 8px;
    }

    .exam-calendar td {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 9px;
        height: 78px;
        text-align: center;
        vertical-align: top;
        padding: 8px 2px;
        color: #334155;
        font-size: 14px;
        overflow-wrap: anywhere;
    }

    .exam-calendar .exam-day {
        background: #fee2e2;
        border: 2px solid #ef4444;
        color: #991b1b;
        font-weight: bold;
    }

    .exam-calendar .today {
        outline: 2px solid #2563eb;
        outline-offset: -3px;
    }

    .exam-label {
        display: block;
        font-size: 10px;
        margin-top: 5px;
    }
    </style>

    <table class="exam-calendar">
    <tr>
    """

    for header in headers:
        calendar_html += f"<th>{header}</th>"

    calendar_html += "</tr>"

    for week in weeks:

        calendar_html += "<tr>"

        for day_number in week:

            if day_number == 0:

                calendar_html += "<td></td>"
                continue

            current_date = date(
                st.session_state.calendar_year,
                st.session_state.calendar_month,
                day_number
            )

            classes = []

            if current_date in exam_dates:
                classes.append("exam-day")

            if current_date == date.today():
                classes.append("today")

            class_text = " ".join(classes)

            calendar_html += (
                f"<td class='{class_text}'>"
                f"<b>{day_number}</b>"
            )

            if current_date in exam_dates:

                for subject_name in exam_dates[current_date]:

                    calendar_html += (
                        "<span class='exam-label'>"
                        "📌 "
                        + html.escape(subject_name)
                        + "</span>"
                    )

            calendar_html += "</td>"

        calendar_html += "</tr>"

    calendar_html += "</table>"

    st.markdown(
        calendar_html,
        unsafe_allow_html=True
    )

    st.caption(
        "🔴 Red = Examination date | "
        "🔵 Blue outline = Today's date"
    )


# ==============================================================
# 12. LIVE EXAM COUNTDOWN TIMER
# ==============================================================

def display_exam_timer(subjects):

    st.subheader("⏳ Live Examination Countdown")

    upcoming = []

    for subject in subjects:

        exam_day = date.fromisoformat(
            subject["exam_date"]
        )

        if exam_day >= date.today():

            upcoming.append(
                (exam_day, subject["name"])
            )

    if not upcoming:

        st.success(
            "All registered examinations are completed!"
        )

        return

    upcoming.sort(key=lambda item: item[0])

    next_date, next_subject = upcoming[0]

    st.markdown(
        f"**Next examination: {html.escape(next_subject)}**"
    )

    if next_date == date.today():

        st.success(
            "🎉 Your examination is today. Best of luck!"
        )

        return

    year = next_date.year
    month = next_date.month
    day = next_date.day

    timer_html = f"""
    <div style="
        background:linear-gradient(120deg,#1e3a8a,#6366f1);
        padding:24px 12px;
        border-radius:18px;
        color:white;
        text-align:center;
        font-family:Arial,sans-serif;
    ">

        <div style="font-size:14px;color:#e0e7ff;">
            TIME REMAINING UNTIL EXAM DAY
        </div>

        <div id="exam-timer" style="
            display:flex;
            justify-content:center;
            gap:12px;
            flex-wrap:wrap;
            margin-top:18px;
        ">
            Loading countdown...
        </div>

        <div style="
            margin-top:18px;
            font-size:13px;
            color:#e0e7ff;
        ">
            Exam date: {next_date.strftime("%d %B %Y")}
        </div>

    </div>

    <script>

    const target = new Date(
        {year}, {month - 1}, {day}, 0, 0, 0
    ).getTime();

    function updateTimer() {{

        const now = new Date().getTime();

        const distance = target - now;

        const display = document.getElementById("exam-timer");

        if (distance <= 0) {{

            display.innerHTML =
                "<div style='font-size:22px;font-weight:bold;'>Exam day!</div>";

            return;
        }}

        const days = Math.floor(
            distance / (1000 * 60 * 60 * 24)
        );

        const hours = Math.floor(
            (distance % (1000 * 60 * 60 * 24)) /
            (1000 * 60 * 60)
        );

        const minutes = Math.floor(
            (distance % (1000 * 60 * 60)) /
            (1000 * 60)
        );

        const seconds = Math.floor(
            (distance % (1000 * 60)) / 1000
        );

        function timerBox(value, label) {{

            return `
                <div style="
                    background:rgba(255,255,255,0.15);
                    border-radius:12px;
                    padding:12px 16px;
                    min-width:65px;
                ">

                    <div style="
                        font-size:28px;
                        font-weight:bold;
                    ">
                        ${{String(value).padStart(2,'0')}}
                    </div>

                    <div style="
                        font-size:11px;
                        color:#e0e7ff;
                    ">
                        ${{label}}
                    </div>

                </div>
            `;
        }}

        display.innerHTML =
            timerBox(days, "DAYS") +
            timerBox(hours, "HOURS") +
            timerBox(minutes, "MINUTES") +
            timerBox(seconds, "SECONDS");

    }}

    updateTimer();

    setInterval(updateTimer, 1000);

    </script>
    """

    components.html(
        timer_html,
        height=190,
        scrolling=False
    )


# ==============================================================
# 13. DOWNLOAD HELPERS
# ==============================================================

def dataframe_to_csv(dataframe):

    return dataframe.to_csv(
        index=False
    ).encode("utf-8")


def create_progress_report():

    rows = []

    for subject_name, topics in (
        st.session_state.study_progress.items()
    ):

        for topic in topics:

            rows.append({

                "Subject": subject_name,

                "Topic": topic["topic"],

                "Status": (
                    "Completed"
                    if topic["completed"]
                    else "Pending"
                )
            })

    return pd.DataFrame(rows)


# ==============================================================
# 14. SIDEBAR NAVIGATION
# ==============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center;padding:15px 5px 25px;">

            <div style="font-size:42px;">🎓</div>

            <h2 style="color:white;margin-bottom:0;">
                SmartStudy AI
            </h2>

            <p style="color:#c7d2fe;font-size:12px;">
                Your Personal Study Companion
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    selected_page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Study Progress",
            "About Project"
        ],
        index=[
            "Dashboard",
            "Study Progress",
            "About Project"
        ].index(st.session_state.page)
    )

    st.session_state.page = selected_page

    st.markdown("---")

    st.markdown("### 📌 Quick Information")

    st.write(
        f"📚 Subjects: {len(get_subjects())}"
    )

    st.write(
        f"⏰ Daily hours: "
        f"{st.session_state.app_data['daily_hours']}"
    )

    st.markdown("---")

    st.caption("SmartStudy AI | Premium Edition")


# ==============================================================
# 15. ABOUT PROJECT PAGE
# ==============================================================

if st.session_state.page == "About Project":

    st.markdown(
        """
        <div class="hero">

            <h1>About SmartStudy AI 🎓</h1>

            <p>
                A personal AI-powered academic planning
                and productivity application.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("Project Overview")

    st.write("""
    SmartStudy AI is an intelligent study planner designed
    to help students organize their academic preparation.

    It combines Python-based timetable generation,
    AI-powered personalized advice, progress tracking
    and data visualization.
    """)

    st.subheader("Technology Stack")

    technology_data = pd.DataFrame({

        "Technology": [
            "Python",
            "Streamlit",
            "Ollama",
            "Llama 3.2",
            "Pandas",
            "Plotly",
            "JSON"
        ],

        "Purpose": [
            "Core programming language",
            "User interface",
            "Local AI model execution",
            "AI study recommendations",
            "Data processing",
            "Interactive visualizations",
            "Data storage"
        ]
    })

    st.dataframe(
        technology_data,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("How the Application Works")

    st.markdown("""
    1. Student enters academic information.
    2. Python processes subject details and exam dates.
    3. A rule-based algorithm generates a study timetable.
    4. Ollama generates personalized study recommendations.
    5. Students update completed topics.
    6. Progress is stored in JSON files.
    7. Plotly visualizes academic progress.
    """)

    st.subheader("Main Objectives")

    st.markdown("""
    - Improve time management.
    - Prioritize upcoming examinations.
    - Encourage regular revision.
    - Track learning progress.
    - Provide personalized AI guidance.
    """)

    st.info(
        "SmartStudy AI supports academic planning. "
        "Students should review and adjust their timetable "
        "according to their actual learning needs."
    )

    st.stop()


# ==============================================================
# 16. STUDY PROGRESS PAGE
# ==============================================================

if st.session_state.page == "Study Progress":

    st.markdown(
        """
        <div class="hero">

            <h1>📈 Study Progress</h1>

            <p>
                Track your learning journey and celebrate
                every completed topic.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    subjects = get_subjects()

    if not subjects:

        st.warning(
            "Please add your subjects from the Dashboard first."
        )

        st.stop()

    initialize_progress()

    overall_progress = get_all_progress()

    st.subheader("Your Learning Overview")

    st.metric(
        "Overall Completion",
        f"{overall_progress}%"
    )

    st.progress(
        overall_progress / 100
    )

    st.divider()

    for subject in subjects:

        name = subject["name"]

        st.markdown(f"### 📘 {name}")

        topics = st.session_state.study_progress.get(
            name,
            []
        )

        for index, topic in enumerate(topics):

            topic_name = topic["topic"]

            current_status = topic["completed"]

            updated_status = st.checkbox(
                topic_name,
                value=current_status,
                key=f"progress_{name}_{index}"
            )

            if updated_status != current_status:

                st.session_state.study_progress[name][index][
                    "completed"
                ] = updated_status

                save_json(
                    PROGRESS_FILE,
                    st.session_state.study_progress
                )

        percentage = get_progress_percentage(name)

        st.progress(
            percentage / 100
        )

        st.caption(
            f"{percentage}% completed"
        )

        with st.form(key=f"add_topic_form_{index}"):
        

            new_topic = st.text_input(
                f"Add a new topic to {name}"
            )

            add_topic = st.form_submit_button(
                "Add Topic"
            )

            if add_topic:

                if new_topic.strip():

                    st.session_state.study_progress[
                        name
                    ].append({

                        "topic": new_topic.strip(),

                        "completed": False
                    })

                    save_json(
                        PROGRESS_FILE,
                        st.session_state.study_progress
                    )

                    st.success("Topic added successfully!")

                    st.rerun()

                else:

                    st.warning("Please enter a topic name.")

        st.divider()

    progress_report = create_progress_report()

    if not progress_report.empty:

        st.download_button(
            "⬇️ Download Progress Report",

            data=dataframe_to_csv(progress_report),

            file_name="SmartStudy_Progress_Report.csv",

            mime="text/csv"
        )

    st.stop()


# ==============================================================
# 17. DASHBOARD
# ==============================================================

st.markdown(
    """
    <div class="hero">

        <h1>Welcome to SmartStudy AI ✨</h1>

        <p>
            Plan smarter, study consistently and achieve
            your academic goals.
        </p>

    </div>
    """,
    unsafe_allow_html=True
)


# ==============================================================
# 18. STUDENT INFORMATION FORM
# ==============================================================

st.subheader("👤 Student Information")

existing_data = st.session_state.app_data

old_subjects = existing_data["subjects"]

with st.form("student_details_form"):

    student_name = st.text_input(
        "Student Name",
        value=existing_data["student_name"],
        placeholder="Enter your name"
    )

    daily_hours = st.slider(
        "Available Study Hours Per Day",
        min_value=1,
        max_value=12,
        value=existing_data["daily_hours"]
    )

    subject_count = st.number_input(
        "Number of Subjects",
        min_value=1,
        max_value=10,
        value=max(1, min(10, len(old_subjects))),
        step=1
    )

    st.markdown("### 📚 Subject Details")

    new_subjects = []

    for index in range(int(subject_count)):

        old_subject = (
            old_subjects[index]
            if index < len(old_subjects)
            else {}
        )

        col1, col2 = st.columns(2)

        with col1:

            subject_name = st.text_input(
                "Subject Name",

                value=old_subject.get("name", ""),

                key=f"subject_name_{index}",

                placeholder="Example: Mathematics"
            )

            try:

                old_exam_date = date.fromisoformat(
                    old_subject.get("exam_date", "")
                )

            except (ValueError, TypeError):

                old_exam_date = (
                    date.today() + timedelta(days=15)
                )

            exam_date = st.date_input(
                "Examination Date",

                value=old_exam_date,

                key=f"exam_date_{index}"
            )

        with col2:

            old_difficulty = old_subject.get(
                "difficulty",
                "Medium"
            )

            difficulty_options = [
                "Easy",
                "Medium",
                "Hard"
            ]

            difficulty = st.selectbox(
                "Difficulty Level",

                difficulty_options,

                index=difficulty_options.index(
                    old_difficulty
                ),

                key=f"difficulty_{index}"
            )

        new_subjects.append({

            "name": subject_name.strip(),

            "exam_date": exam_date.isoformat(),

            "difficulty": difficulty
        })

        st.divider()

    submitted = st.form_submit_button(
        "💾 Save Student Information",
        use_container_width=True
    )


# ==============================================================
# 19. SAVE STUDENT INFORMATION
# ==============================================================

if submitted:

    valid_subjects = [
        subject
        for subject in new_subjects
        if subject["name"]
    ]

    if not student_name.strip():

        st.error("Please enter your name.")

    elif len(valid_subjects) != int(subject_count):

        st.error("Please enter a name for every subject.")

    elif len({
        subject["name"].lower()
        for subject in valid_subjects
    }) != len(valid_subjects):

        st.error("Subject names must be unique.")

    else:

        previous_progress = st.session_state.study_progress

        st.session_state.app_data = {

            "student_name": student_name.strip(),

            "subjects": valid_subjects,

            "daily_hours": daily_hours,

            "created_at": existing_data["created_at"]
        }

        save_current_app_data()

        st.session_state.study_progress = normalize_progress(
            previous_progress,
            valid_subjects
        )

        save_json(
            PROGRESS_FILE,
            st.session_state.study_progress
        )

        st.session_state.ai_advice = None

        st.success(
            "Student information saved successfully!"
        )

        st.rerun()


# ==============================================================
# 20. LOAD DASHBOARD SUBJECTS
# ==============================================================

subjects = get_subjects()

if not subjects:

    st.info(
        "Enter your student information and subjects above "
        "to generate your personalized dashboard."
    )

    st.stop()


initialize_progress()

student_name = st.session_state.app_data["student_name"]

daily_hours = st.session_state.app_data["daily_hours"]


# ==============================================================
# 21. DASHBOARD METRICS
# ==============================================================

st.divider()

st.subheader(
    f"Hello, {student_name}! 👋"
)

st.write(
    "Here is your current academic preparation overview."
)

total_subjects = len(subjects)

upcoming_exams = sum(
    1
    for subject in subjects
    if get_exam_days(subject["exam_date"]) is not None
    and get_exam_days(subject["exam_date"]) >= 0
)

overall_progress = get_all_progress()

next_exam = min(
    subjects,
    key=lambda subject: subject["exam_date"]
)

days_to_next_exam = get_exam_days(
    next_exam["exam_date"]
)

metric1, metric2, metric3, metric4 = st.columns(4)

with metric1:

    st.metric(
        "Total Subjects",
        total_subjects
    )

with metric2:

    st.metric(
        "Upcoming Exams",
        upcoming_exams
    )

with metric3:

    st.metric(
        "Daily Study Goal",
        f"{daily_hours} hrs"
    )

with metric4:

    st.metric(
        "Overall Progress",
        f"{overall_progress}%"
    )


# ==============================================================
# 22. EXAM COUNTDOWN TABLE
# ==============================================================

st.divider()

st.subheader("⏳ Examination Countdown")

exam_rows = []

for subject in subjects:

    days = get_exam_days(
        subject["exam_date"]
    )

    exam_rows.append({

        "Subject": subject["name"],

        "Exam Date": subject["exam_date"],

        "Days Remaining": (
            days if days is not None else "Unavailable"
        ),

        "Difficulty": subject["difficulty"],

        "Status": get_exam_status(days)
    })

exam_df = pd.DataFrame(exam_rows)

st.dataframe(
    exam_df,
    use_container_width=True,
    hide_index=True
)


# ==============================================================
# 23. EXAM CALENDAR AND LIVE TIMER
# ==============================================================

st.divider()

display_exam_calendar(subjects)

st.divider()

display_exam_timer(subjects)


# ==============================================================
# 24. EXAM SCHEDULE ANALYSIS
# ==============================================================

st.divider()

st.subheader("📊 Exam Schedule Analysis")

chart_data = pd.DataFrame([

    {
        "Subject": subject["name"],

        "Days Remaining": get_exam_days(
            subject["exam_date"]
        )
    }

    for subject in subjects
])

chart_data = chart_data.dropna(
    subset=["Days Remaining"]
)

if not chart_data.empty:

    exam_chart = px.bar(

        chart_data,

        x="Subject",

        y="Days Remaining",

        color="Days Remaining",

        color_continuous_scale="Blues",

        text="Days Remaining",

        title="Days Remaining Until Each Examination"
    )

    exam_chart.update_layout(

        template="plotly_white",

        title_x=0.02,

        xaxis_title="Subjects",

        yaxis_title="Days Remaining",

        coloraxis_showscale=False
    )

    exam_chart.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        exam_chart,
        use_container_width=True,
        key="exam_schedule_chart"
    )

else:

    st.info("No examination dates available.")


# ==============================================================
# 25. SUBJECT-WISE PROGRESS CHART
# ==============================================================

st.subheader("📈 Subject-wise Learning Progress")

progress_data = pd.DataFrame([

    {
        "Subject": subject["name"],

        "Completion": get_progress_percentage(
            subject["name"]
        )
    }

    for subject in subjects
])

progress_chart = px.bar(

    progress_data,

    x="Subject",

    y="Completion",

    color="Completion",

    color_continuous_scale="Purples",

    range_y=[0, 100],

    text="Completion",

    title="Topic Completion by Subject"
)

progress_chart.update_layout(

    template="plotly_white",

    title_x=0.02,

    xaxis_title="Subjects",

    yaxis_title="Completion Percentage",

    coloraxis_showscale=False
)

progress_chart.update_traces(
    texttemplate="%{text}%",
    textposition="outside"
)

st.plotly_chart(
    progress_chart,
    use_container_width=True,
    key="subject_progress_chart"
)


# ==============================================================
# 26. SEVEN-DAY STUDY TIMETABLE
# ==============================================================

st.divider()

st.subheader("🗓️ Your Personalized Study Timetable")

st.write(
    "Your timetable is generated using examination dates "
    "and subject difficulty."
)

timetable_df = generate_timetable(
    subjects,
    daily_hours
)

st.dataframe(
    timetable_df,
    use_container_width=True,
    hide_index=True
)

if not timetable_df.empty:

    st.download_button(

        "⬇️ Download Study Timetable",

        data=dataframe_to_csv(timetable_df),

        file_name="SmartStudy_Weekly_Timetable.csv",

        mime="text/csv"
    )


# ==============================================================
# 27. WEEKLY STUDY TIME DISTRIBUTION
# ==============================================================

st.subheader("⏱️ Weekly Time Distribution")

if not timetable_df.empty:

    time_data = pd.DataFrame({

        "Activity": [
            "Study",
            "Practice",
            "Revision"
        ],

        "Hours": [

            timetable_df["Study (hrs)"].sum(),

            timetable_df["Practice (hrs)"].sum(),

            timetable_df["Revision (hrs)"].sum()
        ]
    })

    time_chart = px.pie(

        time_data,

        names="Activity",

        values="Hours",

        hole=0.55,

        title="How Your Study Time Is Distributed"
    )

    time_chart.update_layout(
        template="plotly_white",
        title_x=0.02
    )

    st.plotly_chart(
        time_chart,
        use_container_width=True,
        key="study_time_chart"
    )


# ==============================================================
# 28. AI STUDY ASSISTANT
# ==============================================================

st.divider()

st.markdown(
    """
    <div class="custom-card">

        <h2>🤖 SmartStudy AI Assistant</h2>

        <p>
            Get personalized study strategies and
            intelligent academic recommendations.
        </p>

    </div>
    """,
    unsafe_allow_html=True
)

if st.button(
    "✨ Generate My AI Study Advice",
    use_container_width=True
):

    with st.spinner(
        "SmartStudy AI is preparing your recommendations..."
    ):

        st.session_state.ai_advice = get_ai_advice(
            student_name,
            subjects,
            daily_hours
        )

if st.session_state.ai_advice:

    st.markdown(
        "### Your Personalized Recommendations"
    )

    st.markdown(
        st.session_state.ai_advice
    )


# ==============================================================
# 29. STUDY TIPS
# ==============================================================

st.divider()

st.subheader("🎯 Your Study Summary")

col1, col2 = st.columns(2)

with col1:

    st.markdown(
        """
        <div class="custom-card">

            <h3>📚 Academic Focus</h3>

            <p>
                Focus on subjects with the nearest
                examination dates.
            </p>

            <p>
                Maintain consistent practice and
                daily revision.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.markdown(
        """
        <div class="custom-card">

            <h3>💡 Productivity Tip</h3>

            <p>
                Break large topics into smaller,
                manageable study sessions.
            </p>

            <p>
                Track your progress every day.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# ==============================================================
# 30. FOOTER
# ==============================================================

st.markdown(
    """
    <div class="footer">

        <hr>

        <b>SmartStudy AI</b> |
        Personal AI-Powered Study Planner

        <br>

        Built with Python, Streamlit, Ollama and Plotly

        <br><br>

        Study Smart. Stay Consistent. Achieve More. 🚀

    </div>
    """,
    unsafe_allow_html=True
)
