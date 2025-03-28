import streamlit as st
import fitz  # PyMuPDF
import re
import requests
import json

# Конфигурация API
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
YOUR_SITE_URL = "https://your-site-url.com"  # Укажите ваш URL или заглушку
YOUR_APP_NAME = "Scientific_Annotation_App"

# Захардкоженный промпт
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

# Функция для очистки текста
def clean_text(text):
    text = re.sub(r"\n\d+\n", "\n", text)
    text = re.split(r"(Список литературы|Литература|References)", text, flags=re.IGNORECASE)[0]
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()

# Функция для извлечения текста из PDF
def extract_text_from_pdf(pdf_file):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = "".join([page.get_text() for page in pdf_document])
    pdf_document.close()
    return clean_text(text)

# Функция для вызова OpenRouter API
def call_openrouter_api(prompt):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": YOUR_SITE_URL,
                "X-Title": YOUR_APP_NAME,
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "top_p": 0.9
            })
        )
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Ошибка: Невозможно получить ответ") if response.status_code == 200 else f"Ошибка: {response.status_code}, {response.text}"
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"

# Интерфейс Streamlit
def main():
    st.title("Создание аннотации научной статьи")
    st.write("Вы можете загрузить PDF-файл или ввести текст статьи вручную.")
    
    # Спойлер для загрузки PDF
    with st.expander("Загрузить PDF-файл"):
        uploaded_file = st.file_uploader("Выберите PDF-файл", type=["pdf"])
        pdf_text = ""
        if uploaded_file is not None:
            st.info("Извлечение и очистка текста из PDF...")
            pdf_text = extract_text_from_pdf(uploaded_file)
            if pdf_text.strip():
                st.success("Текст успешно извлечен и очищен!")
                st.text_area("Очищенный текст статьи из PDF:", pdf_text, height=200)
            else:
                st.error("Не удалось извлечь текст из PDF. Проверьте файл.")
    
    # Текстовое поле для ввода статьи вручную
    user_text = st.text_area("Или введите текст статьи вручную:", height=300)
    final_text = user_text.strip() if user_text.strip() else pdf_text.strip()
    
    if final_text:
        if st.button("Сгенерировать аннотацию"):
            st.info("Генерация аннотации...")
            final_prompt = PROMPT_TEMPLATE.format(text=final_text)
            result = call_openrouter_api(final_prompt)
            st.subheader("Сгенерированная аннотация:")
            st.write(result)
    else:
        st.warning("Введите текст статьи вручную или загрузите PDF.")

if __name__ == "__main__":
    main()
