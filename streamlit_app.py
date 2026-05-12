import streamlit as st
import fitz  # PyMuPDF
import re
import requests
import json
import time

st.set_page_config(
    page_title="АннотатоR",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Конфигурация API ──────────────────────────────────────────────────────────
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
YOUR_SITE_URL = "https://your-site-url.com"
YOUR_APP_NAME = "Scientific_Annotation_App"

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

# ── Глобальные стили ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap');

/* Сброс и базовые стили */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* Убираем стандартный отступ Streamlit */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* Скрываем стандартный заголовок и меню */
#MainMenu, footer, header { visibility: hidden; }

/* ── Верхняя панель ── */
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

/* ── Секция-лейбл ── */
.section-label {
    font-size: 10.5px; font-weight: 500; letter-spacing: 0.08em;
    text-transform: uppercase; color: #888780;
    margin-bottom: 10px; margin-top: 20px;
    display: flex; align-items: center; gap: 5px;
}

/* ── Карточки режима инференса ── */
.mode-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 4px; }
.mode-card {
    padding: 12px 14px; border-radius: 8px;
    border: 1px solid #e8e6e0; background: #fff;
    cursor: pointer; transition: border-color .15s;
}
.mode-card.active { border: 1.5px solid #2c2c2a; background: #f5f4f0; }
.mode-card-icon { font-size: 18px; margin-bottom: 6px; }
.mode-card-title { font-size: 12px; font-weight: 500; color: #1a1a18; }
.mode-card-desc  { font-size: 11px; color: #888780; margin-top: 2px; }

/* ── Зона загрузки ── */
.upload-zone {
    border: 1px dashed #b4b2a9;
    border-radius: 10px; padding: 22px;
    text-align: center; background: #fff;
    margin-bottom: 12px;
}
.upload-zone-icon { font-size: 28px; color: #b4b2a9; margin-bottom: 8px; }
.upload-zone-title { font-size: 13px; font-weight: 500; color: #1a1a18; margin-bottom: 3px; }
.upload-zone-hint  { font-size: 11px; color: #888780; }

/* ── Дивайдер ── */
.divider-row {
    display: flex; align-items: center; gap: 10px; margin: 14px 0;
}
.divider-line { flex: 1; height: 1px; background: #e8e6e0; }
.divider-text { font-size: 11px; color: #888780; }

/* ── Карточка результата ── */
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
}
.meta-item { font-size: 11px; color: #888780; display: flex; align-items: center; gap: 4px; }

/* ── Кнопка генерации ── */
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

/* ── Стиль текстовой области ── */
textarea {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 13px !important;
    border: 1px solid #e8e6e0 !important;
    border-radius: 8px !important;
    background: #fff !important;
    color: #1a1a18 !important;
}
textarea:focus { border-color: #888780 !important; box-shadow: none !important; }

/* ── Стиль file_uploader ── */
[data-testid="stFileUploader"] {
    border: 1px dashed #b4b2a9 !important;
    border-radius: 10px !important;
    background: #fff !important;
    padding: 8px !important;
}
[data-testid="stFileUploader"] label { display: none !important; }

/* ── Радиокнопки (режим/модель) ── */
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


/* Колонки: выравнивание по верху, убираем gap */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: 0 !important;
}

/* Правая колонка — граница слева */
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
    border-left: 1px solid #e8e6e0 !important;
}

/* Отступы колонок — через stVerticalBlock (единственный надёжный слой) */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
    padding: 20px 28px 32px !important;
}

/* Убираем лишние отступы внутри markdown-обёрток чтобы не дублировались */
[data-testid="stHorizontalBlock"] .eqmt79k2 {
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stElementContainer"] {
    margin-bottom: 8px !important;
}

</style>
""", unsafe_allow_html=True)


# ── Утилиты ──────────────────────────────────────────────────────────────────
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


def call_openrouter_api(prompt: str, model: str) -> tuple[str, float]:
    model_map = {
        "Llama 3.3 70B": "meta-llama/llama-3.3-70b-instruct:free",
    }
    t0 = time.time()
    try:
        resp = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": YOUR_SITE_URL,
                "X-Title": YOUR_APP_NAME,
            },
            data=json.dumps({
                "model": model_map.get(model, "meta-llama/llama-3.3-70b-instruct:free"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "top_p": 0.9,
            }),
        )
        elapsed = round(time.time() - t0, 1)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"], elapsed
        return f"Ошибка {resp.status_code}: {resp.text}", elapsed
    except Exception as e:
        return f"Ошибка соединения: {e}", 0.0


# ── Инициализация состояния ───────────────────────────────────────────────────
if "annotation" not in st.session_state:
    st.session_state.annotation = ""
if "elapsed" not in st.session_state:
    st.session_state.elapsed = 0.0
if "model_used" not in st.session_state:
    st.session_state.model_used = ""


# ── Топбар ───────────────────────────────────────────────────────────────────
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


# ── Основной макет: две колонки ───────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="small")

# ════════════════════════════════════════════
#  ЛЕВАЯ КОЛОНКА — ввод
# ════════════════════════════════════════════
with col_left:
    # Режим инференса
    st.markdown('<div class="section-label" style="margin-top:0;">⚙ Режим инференса</div>', unsafe_allow_html=True)
    inference_mode = st.radio(
        label="inference_mode",
        options=["☁ Удалённый (OpenRouter)", "🖥 Локальный (llama.cpp)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # Выбор модели — только один вариант, показываем как инфо-пилл
    if "Удалённый" in inference_mode:
        model_choice = "Llama 3.3 70B"
        st.markdown(
            '<div class="section-label">🧠 Модель</div>'
            '<div style="display:inline-flex;align-items:center;gap:6px;'
            'background:#f5f4f0;border:1px solid #2c2c2a;border-radius:20px;'
            'padding:4px 14px;font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:8px;">'
            '✦ Llama 3.3 70B Instruct</div>',
            unsafe_allow_html=True,
        )
    else:
        model_choice = "Локальная модель (llama.cpp)"
        st.info("Локальный сервер: убедитесь, что llama.cpp запущен на порту 8080.")

    # Загрузка PDF
    st.markdown('<div class="section-label">📂 Источник текста</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        label="pdf_upload",
        type=["pdf"],
        label_visibility="collapsed",
    )

    # Дивайдер
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


# ════════════════════════════════════════════
#  ПРАВАЯ КОЛОНКА — результат
# ════════════════════════════════════════════
with col_right:
    st.markdown(
        '<div class="section-label" style="margin-top:0;">≡ Результат</div>',
        unsafe_allow_html=True,
    )

    # ── Логика генерации ─────────────────────────────────────────────────────
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
            with st.spinner("Генерация аннотации…"):
                result, elapsed = call_openrouter_api(
                    PROMPT_TEMPLATE.format(text=final_text),
                    model=model_choice,
                )
            st.session_state.annotation = result
            st.session_state.elapsed    = elapsed
            st.session_state.model_used = model_choice

    # ── Карточка с результатом ───────────────────────────────────────────────
    if st.session_state.annotation:
        ann   = st.session_state.annotation
        words = len(ann.split())
        secs  = st.session_state.elapsed
        model = st.session_state.model_used

        st.markdown(f"""
        <div class="result-card">
          <div class="result-text">{ann}</div>
          <div class="meta-row">
            <div class="meta-item">🕐 {secs} сек.</div>
            <div class="meta-item">📝 {words} слов</div>
            <div class="meta-item">🧠 {model}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Кнопка копирования через st.code (нативный copy)
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        with st.expander("📋 Скопировать текст"):
            st.code(ann, language=None)
    else:
        st.markdown("""
        <div class="result-card" style="min-height:260px; display:flex; align-items:center; justify-content:center;">
          <div class="result-placeholder">
            Здесь появится сгенерированная аннотация.<br>
            Загрузите PDF или введите текст, затем нажмите «Сгенерировать».
          </div>
        </div>
        """, unsafe_allow_html=True)