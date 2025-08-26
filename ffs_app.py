import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import csv
from fpdf import FPDF
import base64
from io import BytesIO

# Конфигурация страницы
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

from fpdf import FPDF
import io
import os

def create_pdf_report(scores, ffs, context, ffs_delta, scores_delta):
    # Создаём PDF
    pdf = FPDF()
    pdf.add_page()

    # Добавляем шрифт с поддержкой кириллицы
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 14)

    # Заголовок
    pdf.cell(200, 10, "Отчёт по FFS", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("DejaVu", "", 12)

    # Основные данные
    pdf.cell(200, 10, f"FFS: {ffs}", ln=True)
    pdf.cell(200, 10, f"Контекст: {context}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, f"Изменение FFS: {ffs_delta}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, "Оценки:", ln=True)

    for key, value in scores.items():
        delta = scores_delta.get(key, 0)
        pdf.cell(200, 10, f"{key}: {value} (Δ {delta})", ln=True)

    # Записываем PDF в память
    pdf_output = io.BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin1")  # fpdf требует latin1
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    return pdf_output

def get_download_link(file_data, filename):
    b64 = base64.b64encode(file_data.read()).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download PDF Report</a>'

# Интерфейс Streamlit
st.title("🧠 Functional Freedom Score Calculator")
st.markdown("Оцените и развивайте свою функциональную свободу через саморефлексию, адаптация, управление и творчество")

# Сайдбар для навигации
st.sidebar.header("Навигация")
section = st.sidebar.radio("Перейти к:", ["Тестирование", "Прогресс", "Рекомендации"])

if section == "Тестирование":
    st.header("Прохождение теста")
    
    # Выбор контекста
    context = st.selectbox("Выберите контекст оценки:", list(WEIGHTS.keys()))
    
    # Отображение весов для выбранного контекста
    with st.expander("Показать весовые коэффициенты для этого контекста"):
        weights_df = pd.DataFrame.from_dict(WEIGHTS[context], orient='index', columns=['Вес'])
        st.dataframe(weights_df.style.format('{:.2f}'))
    
    # Ввод ответов на вопросы
    scores = {}
    st.subheader("Ответьте на вопросы (оценка от 0 до 10)")
    
    for comp in ["R", "C", "H", "T"]:
        st.markdown(f"### {comp} - {['Рефлексия', 'Коррекция', 'Управление', 'Творчество'][['R', 'C', 'H', 'T'].index(comp)]}")
        
        comp_scores = []
        for i, q in enumerate(QUESTIONS[comp]):
            score = st.slider(f"{i+1}. {q}", 0, 10, 5, key=f"{comp}_{i}")
            comp_scores.append(score)
        
        scores[comp] = np.mean(comp_scores)
    
    # Расчет и отображение результатов
    if st.button("Рассчитать FFS"):
        ffs = calculate_ffs(scores, context)
        
        # Сравнение с предыдущим результатом
        ffs_delta, scores_delta = get_comparison_with_previous(ffs, scores)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if ffs_delta is not None:
                st.metric("Общий FFS", f"{ffs:.2f}", f"{ffs_delta:+.2f}")
            else:
                st.metric("Общий FFS", f"{ffs:.2f}")
            
            for comp, score in scores.items():
                delta_text = f"{scores_delta[comp]:+.1f}" if scores_delta and comp in scores_delta else None
                st.progress(score/10, text=f"{comp}: {score:.1f}/10 {delta_text if delta_text else ''}")
        
        with col2:
            fig = plot_radar(scores, ffs)
            st.pyplot(fig)
        
        # Рекомендации
        st.subheader("Персональные рекомендации")
        for comp, score in scores.items():
            if score < 7:
                st.markdown(f"**{comp} - {['Рефлексия', 'Коррекция', 'Управление', 'Творчество'][['R', 'C', 'H', 'T'].index(comp)]}**")
                for rec in RECOMMENDATIONS[comp]:
                    st.markdown(f"- {rec}")
        
        # Генерация PDF отчета
        pdf_report = create_pdf_report(scores, ffs, context, ffs_delta, scores_delta)
        st.markdown(get_download_link(pdf_report, "ffs_report.pdf"), unsafe_allow_html=True)
        
        # Сохранение результатов
        save_results(scores, ffs, context)
        st.success("Результаты сохранены!")

elif section == "Прогресс":
    st.header("История и прогресс")
    
    df = load_history()
    
    if df.empty:
        st.info("История тестирований отсутствует. Пройдите тест для отслеживания прогресса.")
    else:
        # Выбор контекста для фильтрации
        contexts = st.multiselect("Фильтр по контекстам:", options=df["context"].unique(), default=df["context"].unique())
        
        # Выбор компонентов для отображения
        components = st.multiselect(
            "Выберите компоненты для отображения:",
            options=["R", "C", "H", "T", "FFS"],
            default=["FFS", "R", "C", "H", "T"]
        )
        
        if contexts and components:
            filtered_df = df[df["context"].isin(contexts)]
            
            # График прогресса
            st.subheader("Динамика показателей")
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for context in contexts:
                context_data = filtered_df[filtered_df["context"] == context]
                
                for comp in components:
                    if comp == "FFS":
                        ax.plot(context_data["timestamp"], context_data[comp], marker='o', label=f"{context} - FFS")
                    else:
                        comp_name = ["Рефлексия", "Коррекция", "Управление", "Творчество"][["R", "C", "H", "T"].index(comp)]
                        ax.plot(context_data["timestamp"], context_data[comp], marker='o', label=f"{context} - {comp_name}")
            
            ax.set_title("Изменение показателей с течением времени")
            ax.set_xlabel("Дата")
            ax.set_ylabel("Баллы")
            ax.legend()
            ax.grid(True)
            plt.xticks(rotation=45)
            st.pyplot(fig)
            
            # Статистика
            st.subheader("Статистика")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Количество тестирований", len(filtered_df))
            
            with col2:
                latest_ffs = filtered_df["FFS"].iloc[-1]
                prev_ffs = filtered_df["FFS"].iloc[-2] if len(filtered_df) > 1 else latest_ffs
                delta = latest_ffs - prev_ffs
                st.metric("Последний FFS", f"{latest_ffs:.2f}", f"{delta:+.2f}")
            
            with col3:
                st.metric("Средний FFS", f"{filtered_df['FFS'].mean():.2f}")

elif section == "Рекомендации":
    st.header("Персональные рекомендации по развитию")
    
    df = load_history()
    
    if df.empty:
        st.info("История тестирований отсутствует. Пройдите тест для получения рекомендаций.")
    else:
        # Анализ последних результатов
        latest = df.iloc[-1]
        scores = {comp: latest[comp] for comp in ["R", "C", "H", "T"]}
        
        st.subheader("Общие рекомендации")
        for comp, score in scores.items():
            if score < 7:
                comp_name = ["Рефлексия", "Коррекция", "Управление", "Творчество"][["R", "C", "H", "T"].index(comp)]
                st.markdown(f"### {comp_name} ({score:.1f}/10)")
                
                for i, rec in enumerate(RECOMMENDATIONS[comp]):
                    st.markdown(f"{i+1}. {rec}")
                
                st.markdown("---")
        
        # Рекомендации по улучшению
        st.subheader("План развития")
        
        weak_components = [comp for comp, score in scores.items() if score < 7]
        if weak_components:
            st.write("Сфокусируйтесь на развитии этих компонентов:")
            for comp in weak_components:
                comp_name = ["Рефлексия", "Коррекция", "Управление", "Творчество"][["R", "C", "H", "T"].index(comp)]
                st.markdown(f"- **{comp_name}**")
            
            st.write("Рекомендуемый график работы:")
            st.markdown("""
            1. Выделите 15-20 минут daily для практики
            2. Начните с самого слабого компонента
            3. Отслеживайте прогресс через неделю
            4. Корректируйте подход на основе результатов
            """)
        else:
            st.success("Все ваши компоненты развиты хорошо! Продолжайте поддерживать баланс и развивать сильные стороны.")
        
        # Кнопка для генерации PDF отчета
        if st.button("Сгенерировать PDF отчет с рекомендациями"):
            pdf_report = create_pdf_report(scores, latest["FFS"], latest["context"])
            st.markdown(get_download_link(pdf_report, "ffs_recommendations.pdf"), unsafe_allow_html=True)

# Футер
st.markdown("---")
st.markdown("FFS Calculator © 2023 | Разработано для оценки и развития функциональной свободы")
