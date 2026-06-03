import streamlit as st
import fitz  # PyMuPDF
import re
import time
from google import genai
from groq import Groq

st.set_page_config(
    page_title="АннотатоR",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -- Конфигурация API ----------------------------------------------------------
GROQ_API_KEY   = st.secrets.get("GROQ_API_KEY")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")

LOCAL_HOST = "vm-6786.user-project-1031.cloud.intcld.ru"
LOCAL_PORT = 8000

PROMPT_TEMPLATE = """
# Задача: Создание аннотации научной статьи

Напишите аннотацию к научной статье на **РУССКОМ языке**, отражающую ключевые аспекты исследования. Аннотация должна быть лаконичной, содержательной и соответствовать стилю научного изложения. **Не включайте заголовок "Аннотация".**

## Требования
- Используйте следующие речевые шаблоны:
  - «В статье исследуется, анализируется, рассматривается…»;
  - «Статья дает анализ…, подробно освещает…»;
  - «В работе дан анализ (...), раскрыты понятия (...), предложены (...)»;
  - «Статья посвящена…»;
  - «Автор статьи предполагает, характеризует...»;
  - «Используя (...), автор в своих исследованиях доказывает (...)»;
  - «В статье раскрывается, описывается, уделяется внимание…».
- **Не добавляйте личных интерпретаций**, гипотез или выводов, не содержащихся в оригинальном тексте статьи.
- Сохраняйте формальную, нейтральную и научную тональность.

## Входные данные
**Текст статьи:**
"{text}"

## Выходные данные
Только текст аннотации.
"""

# -- Глобальные стили ----------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap" rel="stylesheet">

<style>
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
}

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

#MainMenu, footer, header { visibility: hidden; }

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    height: 52px;
    background: #ffffff;
    border-bottom: 1px solid #e8e6e0;
    position: sticky;
    top: 0;
    z-index: 100;
}
.topbar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}
.topbar-icon {
    width: 28px; height: 28px;
    background: #2c2c2a;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; color: #fff;
}
.topbar-name { font-size: 14px; font-weight: 500; color: #1a1a18; }
.topbar-sub  { font-size: 11px; color: #888780; }
.status-pill {
    font-size: 11px; font-weight: 500;
    padding: 4px 12px; border-radius: 20px;
    background: #eaf3de; color: #3b6d11;
    border: 1px solid #c0dd97;
    display: flex; align-items: center; gap: 5px;
}
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #639922; }

.section-label {
    font-size: 10.5px; font-weight: 500; letter-spacing: 0.08em;
    text-transform: uppercase; color: #888780;
    margin-bottom: 10px; margin-top: 20px;
    display: flex; align-items: center; gap: 5px;
}
.section-label .material-icons {
    font-size: 14px;
    color: #b4b2a9;
    vertical-align: middle;
    line-height: 1;
}

.upload-zone {
    border: 1px dashed #b4b2a9;
    border-radius: 10px; padding: 22px;
    text-align: center; background: #fff;
    margin-bottom: 12px;
}

.divider-row {
    display: flex; align-items: center; gap: 10px; margin: 14px 0;
}
.divider-line { flex: 1; height: 1px; background: #e8e6e0; }
.divider-text { font-size: 11px; color: #888780; }

.result-card {
    background: #fafaf8; border: 1px solid #d3d1c7;
    border-radius: 10px; padding: 20px;
}
.result-header {
    display: flex; align-items: center;
    justify-content: space-between; margin-bottom: 14px;
}
.result-text {
    font-size: 13.5px; color: #1a1a18;
    line-height: 1.8; white-space: pre-wrap;
}
.result-placeholder { font-size: 13px; color: #b4b2a9; font-style: italic; }
.meta-row {
    display: flex; gap: 14px; margin-top: 14px;
    padding-top: 12px; border-top: 1px solid #e8e6e0;
    flex-wrap: wrap;
}
.meta-item {
    font-size: 11px; color: #888780;
    display: flex; align-items: center; gap: 4px;
}
.meta-item .material-icons {
    font-size: 13px;
    color: #b4b2a9;
    vertical-align: middle;
    line-height: 1;
}

div[data-testid="stButton"] > button {
    width: auto !important;
    background: #2c2c2a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 22px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    letter-spacing: 0.01em !important;
    cursor: pointer !important;
    transition: background .15s !important;
}
div[data-testid="stButton"] > button:hover {
    background: #444441 !important;
}

textarea {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 13px !important;
    border: 1px solid #e8e6e0 !important;
    border-radius: 8px !important;
    background: #fff !important;
    color: #1a1a18 !important;
}
textarea:focus { border-color: #888780 !important; box-shadow: none !important; }

[data-testid="stFileUploader"] {
    border: 1px dashed #b4b2a9 !important;
    border-radius: 10px !important;
    background: #fff !important;
    padding: 8px !important;
}
[data-testid="stFileUploader"] label { display: none !important; }

div[data-testid="stRadio"] > div {
    flex-direction: row !important;
    gap: 8px !important;
    flex-wrap: wrap !important;
}
div[data-testid="stRadio"] label {
    background: #fff !important;
    border: 1px solid #e8e6e0 !important;
    border-radius: 20px !important;
    padding: 4px 14px !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    margin: 0 !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background: #f5f4f0 !important;
    border-color: #2c2c2a !important;
    color: #1a1a18 !important;
}

[data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: 0 !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
    border-left: 1px solid #e8e6e0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
    padding: 20px 28px 32px !important;
}
[data-testid="stHorizontalBlock"] .eqmt79k2 {
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stElementContainer"] {
    margin-bottom: 8px !important;
}
</style>
""", unsafe_allow_html=True)


# -- Утилиты -------------------------------------------------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"\n\d+\n", "\n", text)
    text = re.split(r"(Список литературы|Литература|References)", text, flags=re.IGNORECASE)[0]
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_file) -> str:
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return clean_text(text)


def call_groq_api(prompt: str) -> tuple[str, float]:
    t0 = time.time()
    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_completion_tokens=1024,
            top_p=0.9,
            stream=False,
        )
        elapsed = round(time.time() - t0, 1)
        return completion.choices[0].message.content, elapsed
    except Exception as e:
        return f"Ошибка Groq: {e}", 0.0


def call_gemini_api(prompt: str) -> tuple[str, float]:
    t0 = time.time()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        elapsed = round(time.time() - t0, 1)
        return response.text, elapsed
    except Exception as e:
        return f"Ошибка Gemini: {e}", 0.0


def call_local_api(prompt: str) -> tuple[str, float]:
    import requests, json
    t0 = time.time()
    try:
        resp = requests.post(
            url=f"http://{LOCAL_HOST}:{LOCAL_PORT}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 350,
                "repeat_penalty": 1.1,
            }),
            timeout=1200,
        )
        elapsed = round(time.time() - t0, 1)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"], elapsed
        return f"Ошибка сервера {resp.status_code}: {resp.text}", elapsed
    except requests.exceptions.ConnectionError:
        return f"Не удалось подключиться к {LOCAL_HOST}:{LOCAL_PORT}. Убедитесь, что сервер запущен.", 0.0
    except requests.exceptions.Timeout:
        return "Превышено время ожидания ответа от локального сервера.", 0.0
    except Exception as e:
        return f"Ошибка: {e}", 0.0


# -- Инициализация состояния ---------------------------------------------------
if "annotation" not in st.session_state:
    st.session_state.annotation = ""
if "elapsed" not in st.session_state:
    st.session_state.elapsed = 0.0
if "model_used" not in st.session_state:
    st.session_state.model_used = ""


# -- Топбар --------------------------------------------------------------------
st.markdown("""
<div class="topbar">
  <div class="topbar-logo">
    <div class="topbar-icon">📄</div>
    <div>
      <div class="topbar-name">АннотатоR</div>
      <div class="topbar-sub">Генератор научных аннотаций</div>
    </div>
  </div>
  <div class="status-pill">
    <div class="status-dot"></div> API подключён
  </div>
</div>
""", unsafe_allow_html=True)


# -- Основной макет: две колонки -----------------------------------------------
col_left, col_right = st.columns([1, 1], gap="small")

# =============================================
#  ЛЕВАЯ КОЛОНКА — ввод
# =============================================
with col_left:
    st.markdown('<div class="section-label" style="margin-top:0;">⚙ Режим инференса</div>', unsafe_allow_html=True)
    inference_mode = st.radio(
        label="inference_mode",
        options=["☁ Удалённый (облако)", "🖥 Локальный (llama.cpp)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if "Удалённый" in inference_mode:
        st.markdown(
            '<div class="section-label">'
            '<span class="material-icons">smart_toy</span>'
            'Модель'
            '</div>',
            unsafe_allow_html=True,
        )
        provider_choice = st.radio(
            label="provider_choice",
            options=["Llama 3.3 70B (Groq)", "Gemini Flash (Google)"],
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        provider_choice = "local"

    st.markdown(
        '<div class="section-label">'
        '<span class="material-icons">upload_file</span>'
        'Источник текста:'
        '</div>',
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        label="pdf_upload",
        type=["pdf"],
        label_visibility="collapsed",
    )

    st.markdown("""
    <div class="divider-row">
      <div class="divider-line"></div>
      <div class="divider-text">или введите текст</div>
      <div class="divider-line"></div>
    </div>
    """, unsafe_allow_html=True)

    text_input = st.text_area(
        label="manual_text",
        placeholder="Вставьте текст научной статьи здесь…",
        height=180,
        label_visibility="collapsed",
    )

    char_count = len(text_input) if text_input else 0
    st.markdown(
        f'<div style="text-align:right;font-size:11px;color:#888780;margin-top:4px;">'
        f'{char_count:,} / ~15 000 символов</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    generate = st.button("✦ Сгенерировать аннотацию")


# =============================================
#  ПРАВАЯ КОЛОНКА — результат
# =============================================
with col_right:
    st.markdown(
        '<div class="section-label" style="margin-top:0;">'
        '<span class="material-icons">subject</span>'
        'Результат'
        '</div>',
        unsafe_allow_html=True,
    )

    if generate:
        if uploaded_file:
            with st.spinner("Извлечение текста из PDF…"):
                final_text = extract_text_from_pdf(uploaded_file)
        elif text_input.strip():
            final_text = clean_text(text_input)
        else:
            st.error("Загрузите PDF или введите текст статьи.")
            final_text = ""

        if final_text:
            prompt = PROMPT_TEMPLATE.format(text=final_text)
            with st.spinner("Генерация аннотации…"):
                if provider_choice == "local":
                    result, elapsed = call_local_api(prompt)
                    model_label = "YandexGPT Lite (дообученная)"
                elif "Groq" in provider_choice:
                    result, elapsed = call_groq_api(prompt)
                    model_label = "Llama 3.3 70B (Groq)"
                else:
                    result, elapsed = call_gemini_api(prompt)
                    model_label = "Gemini Flash (Google)"
            st.session_state.annotation = result.strip()
            st.session_state.elapsed    = elapsed
            st.session_state.model_used = model_label

    if st.session_state.annotation:
        ann   = st.session_state.annotation
        words = len(ann.split())
        secs  = st.session_state.elapsed
        model = st.session_state.model_used

        st.markdown(f"""
        <div class="result-card">
          <div class="result-text">{ann}</div>
          <div class="meta-row">
            <div class="meta-item">
              <span class="material-icons">timer</span>
              Время генерации: {secs} сек.
            </div>
            <div class="meta-item">
              <span class="material-icons">format_list_numbered</span>
              Длина аннотации: {words} слов
            </div>
            <div class="meta-item">
              <span class="material-icons">smart_toy</span>
              Модель: {model}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

        st.components.v1.html(
            f"""
            <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&display=swap" rel="stylesheet">
            <button onclick="navigator.clipboard.writeText({repr(ann)}).then(() => {{
                this.textContent = 'Скопировано';
                setTimeout(() => this.textContent = 'Скопировать текст', 2000);
            }})" style="
                background: #2c2c2a;
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: 500;
                font-family: 'IBM Plex Sans', sans-serif;
                letter-spacing: 0.01em;
                cursor: pointer;
                transition: background .15s;
            ">Скопировать текст</button>
            """,
            height=50,
        )
    else:
        st.markdown("""
        <div class="result-card" style="min-height:260px; display:flex; align-items:center; justify-content:center;">
          <div class="result-placeholder">
            Здесь появится сгенерированная аннотация.<br><br>
            Загрузите PDF или введите текст,<br>затем нажмите на кнопку «Сгенерировать аннотацию».
          </div>
        </div>
        """, unsafe_allow_html=True)