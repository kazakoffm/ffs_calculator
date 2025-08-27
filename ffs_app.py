# --- системные фиксы ДО импорта streamlit ---
import os
# Отключаем файловый watcher, чтобы не ловить "inotify watch limit reached" на Streamlit Cloud
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import csv
from fpdf import FPDF
import base64
from io import BytesIO

# ===================== УТИЛИТЫ ДЛЯ БЕЗОПАСНОГО PDF =====================

# Простая транслитерация кириллицы → латиница (чтобы fpdf не падал на Юникоде)
_CYR_MAP = str.maketrans({
    "А":"A","Б":"B","В":"V","Г":"G","Д":"D","Е":"E","Ё":"E","Ж":"Zh","З":"Z","И":"I",
    "Й":"Y","К":"K","Л":"L","М":"M","Н":"N","О":"O","П":"P","Р":"R","С":"S","Т":"T",
    "У":"U","Ф":"F","Х":"Kh","Ц":"Ts","Ч":"Ch","Ш":"Sh","Щ":"Shch","Ъ":"","Ы":"Y",
    "Ь":"","Э":"E","Ю":"Yu","Я":"Ya",
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i",
    "й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t",
    "у":"u","ф":"f","х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y",
    "ь":"","э":"e","ю":"yu","я":"ya",
    "’":"'", "“":'"', "”":'"', "«":'"', "»":'"', "—":"-", "–":"-"
})

def _to_pdf_safe(text: str) -> str:
    """Возвращает строку, безопасную для fpdf (latin-1). Если не влезает — транслитерирует."""
    if text is None:
        return ""
    try:
        text.encode("latin-1")
        return text  # уже совместимо
    except UnicodeEncodeError:
        t = text.translate(_CYR_MAP)
        # финальная страховка: заменим непреобразуемые символы вопросительным знаком
        return t.encode("latin-1", "replace").decode("latin-1")

# ===================== КОНФИГ СТРАНИЦЫ =====================

st.set_page_config(
    page_title="FFS Calculator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Весовые коэффициенты для контекстов
WEIGHTS = {
    "personal_growth": {"R": 0.3, "C": 0.3, "H": 0.2, "T": 0.2},
    "creativity": {"R": 0.2, "C": 0.2, "H": 0.2, "T": 0.4},
    "ethics": {"R": 0.35, "C": 0.3, "H": 0.25, "T": 0.1},
    "ai": {"R": 0.25, "C": 0.3, "H": 0.25, "T": 0.2}
}

# Рекомендации по компонентам
RECOMMENDATIONS = {
    "R": [
        "Ведите дневник рефлексии: записывайте мысли и анализируйте принятые решения",
        "Практикуйте медитацию для развития осознанности",
        "Перед важными решениями, анализируйте возможные последствия разных вариантов"
    ],
    "C": [
        "Создайте привычку анализировать ошибки и извлекать из них уроки",
        "Экспериментируйте с новыми подходами в привычных ситуациях",
        "Регулярно получайте обратную связь и работайте с ней"
    ],
    "H": [
        "Используйте техники тайм-менеджмента (например, матрицу Эйзенхауэра)",
        "Развивайте эмоциональный интеллект для лучшего управления импульсами",
        "Практикуйтесь в расстановке приоритетов и планировании сложных задач"
    ],
    "T": [
        "Выделите время для регулярных мозговых штурмов",
        "Изучайте смежные области знаний для генерации новых идей",
        "Практикуйте технику «случайного стимула» для поиска неочевидных решений"
    ]
}

# Вопросы
QUESTIONS = {
    "R": [
        "Насколько легко вы прогнозируете последствия своих действий?",
        "Насколько часто вы анализируете причины эмоций и решений?",
        "Можете ли представить себя в альтернативных сценариях?",
        "Насколько вы понимаете свои долгосрочные цели?",
        "Насколько осознанно вы принимаете решения в стрессе?"
    ],
    "C": [
        "Насколько быстро вы учитесь на ошибках?",
        "Насколько легко меняете привычки при необходимости?",
        "Насколько гибко вы реагируете на новые условия?",
        "Можете ли корректировать поведение под обратную связь?",
        "Насколько вы готовы экспериментировать?"
    ],
    "H": [
        "Насколько хорошо справляетесь с многозадачностью?",
        "Можете ли переключаться между краткосрочными и долгосрочными целями?",
        "Насколько вы управляете импульсами?",
        "Можете ли координировать действия нескольких людей?",
        "Насколько структурированно вы планируете проекты?"
    ],
    "T": [
        "Насколько часто генерируете новые идеи?",
        "Насколько ваши решения оригинальны?",
        "Можете ли сочетать разные идеи для нового?",
        "Насколько часто ваши идеи полезны?",
        "Насколько легко находите неожиданные подходы?"
    ]
}

def calculate_ffs(scores, context):
    weights = WEIGHTS[context]
    return sum(weights[comp] * scores[comp] for comp in scores)

def save_results(scores, ffs, context):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("ffs_history.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, context, scores["R"], scores["C"], scores["H"], scores["T"], ffs])

def plot_radar(scores, ffs):
    labels = list(scores.keys())
    values = list(scores.values())
    values += values[:1]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 10)
    ax.set_title(f"Functional Freedom Score: {ffs:.2f}", size=14, weight='bold')

    return fig

def load_history():
    try:
        df = pd.read_csv("ffs_history.csv", names=["timestamp", "context", "R", "C", "H", "T", "FFS"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except FileNotFoundError:
        return pd.DataFrame()

def get_comparison_with_previous(current_ffs, current_scores):
    df = load_history()
    if len(df) > 1:
        previous = df.iloc[-2]  # Предыдущий результат
        ffs_delta = current_ffs - previous["FFS"]
        scores_delta = {
            comp: current_scores[comp] - previous[comp]
            for comp in ["R", "C", "H", "T"]
        }
        return ffs_delta, scores_delta
    return None, None

def create_pdf_report(scores, ffs, context, ffs_delta=None, scores_delta=None):
    pdf = FPDF()
    pdf.add_page()

    # Заголовок
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, _to_pdf_safe("FFS Assessment Report"), 0, 1, "C")
    pdf.ln(10)

    # Основная информация
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, _to_pdf_safe(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), 0, 1)
    pdf.cell(0, 10, _to_pdf_safe(f"Context: {context}"), 0, 1)
    pdf.cell(0, 10, _to_pdf_safe(f"Overall FFS: {ffs:.2f}"), 0, 1)

    if ffs_delta is not None:
        change_text = f"Change from previous: {ffs_delta:+.2f}"
        pdf.cell(0, 10, _to_pdf_safe(change_text), 0, 1)

    pdf.ln(10)

    # Компоненты
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, _to_pdf_safe("Component Scores:"), 0, 1)
    pdf.set_font("Arial", "", 12)

    for comp in ["R", "C", "H", "T"]:
        comp_name = ["Reflection", "Correction", "Management", "Creativity"][["R", "C", "H", "T"].index(comp)]
        score_text = f"{comp_name}: {scores[comp]:.1f}/10"
        if scores_delta and comp in scores_delta:
            score_text += f" ({scores_delta[comp]:+.1f})"
        pdf.cell(0, 10, _to_pdf_safe(score_text), 0, 1)

    pdf.ln(10)

    # Рекомендации
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, _to_pdf_safe("Recommendations:"), 0, 1)
    pdf.set_font("Arial", "", 12)

    for comp, score in scores.items():
        if score < 7:
            comp_name = ["Reflection", "Correction", "Management", "Creativity"][["R", "C", "H", "T"].index(comp)]
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, _to_pdf_safe(f"{comp_name}:"), 0, 1)
            pdf.set_font("Arial", "", 12)
            for rec in RECOMMENDATIONS[comp]:
                pdf.multi_cell(0, 10, _to_pdf_safe(f"- {rec}"))
            pdf.ln(3)

    # Сохраняем PDF в байтовый объект
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
    pdf_output = BytesIO(pdf_bytes)
    pdf_output.seek(0)
    return pdf_output

def get_download_link(file_data, filename):
    pos = file_data.tell()
    file_data.seek(0)
    b64 = base64.b64encode(file_data.read()).decode()
    file_data.seek(pos)
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download PDF Report</a>'

# ===================== UI =====================

st.title("🧠 Functional Freedom Score Calculator")
st.markdown("Оцените и развивайте свою функциональную свободу через саморефлексию, адаптацию, управление и творчество")

st.sidebar.header("Навигация")
section = st.sidebar.radio("Перейти к:", ["Тестирование", "Прогресс", "Рекомендации"])

if section == "Тестирование":
    st.header("Прохождение теста")

    context = st.selectbox("Выберите контекст оценки:", list(WEIGHTS.keys()))

    with st.expander("Показать весовые коэффициенты для этого контекста"):
        weights_df = pd.DataFrame.from_dict(WEIGHTS[context], orient='index', columns=['Вес'])
        st.dataframe(weights_df.style.format('{:.2f}'))

    # Ответы
    scores = {}
    st.subheader("Ответьте на вопросы (оценка от 0 до 10)")

    for comp in ["R", "C", "H", "T"]:
        st.markdown(f"### {comp} - {['Рефлексия', 'Коррекция', 'Управление', 'Творчество'][['R', 'C', 'H', 'T'].index(comp)]}")
        comp_scores = []
        for i, q in enumerate(QUESTIONS[comp]):
            score = st.slider(f"{i+1}. {q}", 0, 10, 5, key=f"{comp}_{i}")
            comp_scores.append(score)
        scores[comp] = float(np.mean(comp_scores))

    if st.button("Рассчитать FFS"):
        ffs = float(calculate_ffs(scores, context))
        ffs_delta, scores_delta = get_comparison_with_previous(ffs, scores)

        col1, col2 = st.columns(2)
        with col1:
            if ffs_delta is not None:
                st.metric("Общий FFS", f"{ffs:.2f}", f"{ffs_delta:+.2f}")
            else:
                st.metric("Общий FFS", f"{ffs:.2f}")

            # progress(text=...) может отсутствовать в старых версиях, поэтому показываем подписи отдельно
            for comp, score in scores.items():
                st.write(f"{comp}: {score:.1f}/10" + (f"  ({scores_delta[comp]:+.1f})" if scores_delta and comp in scores_delta else ""))
                st.progress(score / 10)

        with col2:
            fig = plot_radar(scores, ffs)
            st.pyplot(fig)

        st.subheader("Персональные рекомендации")
        for comp, score in scores.items():
            if score < 7:
                st.markdown(f"**{comp} - {['Рефлексия', 'Коррекция', 'Управление', 'Творчество'][['R', 'C', 'H', 'T'].index(comp)]}**")
                for rec in RECOMMENDATIONS[comp]:
                    st.markdown(f"- {rec}")

        # Генерация PDF отчета
        try:
            pdf_report = create_pdf_report(scores, ffs, context, ffs_delta, scores_delta)
            st.markdown(get_download_link(pdf_report, "ffs_report.pdf"), unsafe_allow_html=True)
        except Exception as e:
            st.error("Не удалось сформировать PDF. Но сам расчёт выполнен. Сообщение для разработчика: " + str(e))

        # Сохранение результатов
        save_results(scores, ffs, context)
        st.success("Результаты сохранены!")

elif section == "Прогресс":
    st.header("История и прогресс")
    df = load_history()

    if df.empty:
        st.info("История тестирований отсутствует. Пройдите тест для отслеживания прогресса.")
    else:
        contexts = st.multiselect("Фильтр по контекстам:", options=df["context"].unique(), default=list(df["context"].unique()))
        components = st.multiselect(
            "Выберите компоненты для отображения:",
            options=["R", "C", "H", "T", "FFS"],
            default=["FFS", "R", "C", "H", "T"]
        )

        if contexts and components:
            filtered_df = df[df["context"].isin(contexts)]
            st.subheader("Динамика показателей")
            fig, ax = plt.subplots(figsize=(10, 6))

            for ctx in contexts:
                context_data = filtered_df[filtered_df["context"] == ctx]
                for comp in components:
                    label = f"{ctx} - {'FFS' if comp=='FFS' else ['Рефлексия','Коррекция','Управление','Творчество'][['R','C','H','T'].index(comp)]}"
                    ax.plot(context_data["timestamp"], context_data[comp], marker='o', label=label)

            ax.set_title("Изменение показателей с течением времени")
            ax.set_xlabel("Дата")
            ax.set_ylabel("Баллы")
            ax.legend()
            ax.grid(True)
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.subheader("Статистика")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Количество тестирований", len(filtered_df))
            with col2:
                latest_ffs = float(filtered_df["FFS"].iloc[-1])
                prev_ffs = float(filtered_df["FFS"].iloc[-2]) if len(filtered_df) > 1 else latest_ffs
                st.metric("Последний FFS", f"{latest_ffs:.2f}", f"{(latest_ffs - prev_ffs):+.2f}")
            with col3:
                st.metric("Средний FFS", f"{filtered_df['FFS'].mean():.2f}")

elif section == "Рекомендации":
    st.header("Персональные рекомендации по развитию")
    df = load_history()

    if df.empty:
        st.info("История тестирований отсутствует. Пройдите тест для получения рекомендаций.")
    else:
        latest = df.iloc[-1]
        scores = {comp: float(latest[comp]) for comp in ["R", "C", "H", "T"]}

        st.subheader("Общие рекомендации")
        for comp, score in scores.items():
            if score < 7:
                comp_name = ["Рефлексия", "Коррекция", "Управление", "Творчество"][["R", "C", "H", "T"].index(comp)]
                st.markdown(f"### {comp_name} ({score:.1f}/10)")
                for i, rec in enumerate(RECOMMENDATIONS[comp]):
                    st.markdown(f"{i+1}. {rec}")
                st.markdown("---")

        st.subheader("План развития")
        weak_components = [comp for comp, score in scores.items() if score < 7]
        if weak_components:
            st.write("Сфокусируйтесь на развитии этих компонентов:")
            for comp in weak_components:
                comp_name = ["Рефлексия", "Коррекция", "Управление", "Творчество"][["R", "C", "H", "T"].index(comp)]
                st.markdown(f"- **{comp_name}**")
            st.write("Рекомендуемый график работы:")
            st.markdown("""
            1. Выделите 15–20 минут ежедневно для практики  
            2. Начните с самого слабого компонента  
            3. Отслеживайте прогресс через неделю  
            4. Корректируйте подход на основе результатов  
            """)
        else:
            st.success("Все ваши компоненты развиты хорошо! Поддерживайте баланс и развивайте сильные стороны.")

        if st.button("Сгенерировать PDF отчет с рекомендациями"):
            try:
                pdf_report = create_pdf_report(scores, float(latest["FFS"]), str(latest["context"]))
                st.markdown(get_download_link(pdf_report, "ffs_recommendations.pdf"), unsafe_allow_html=True)
            except Exception as e:
                st.error("Не удалось сформировать PDF. Сообщение для разработчика: " + str(e))

# Футер
st.markdown("---")
st.markdown("FFS Calculator © 2023 | Разработано для оценки и развития функциональной свободы")
