import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
PDF_PATH = BACKEND_DIR / "data" / "Bella_Vista_Restaurant_Knowledge_Base.pdf"
NOT_FOUND_MESSAGE = "I could not find that information in the Bella Vista knowledge base."

load_dotenv(BACKEND_DIR / ".env")

for secret_name in ("GROQ_API_KEY", "GROQ_MODEL"):
    try:
        if secret_name in st.secrets and not os.getenv(secret_name):
            os.environ[secret_name] = st.secrets[secret_name]
    except Exception:
        pass


st.set_page_config(
    page_title="Bella Vista Chatbot",
    page_icon="BV",
    layout="centered",
)


MENU_ITEMS = {
    "margherita pizza": "$10 - Tomato Sauce, Mozzarella, Basil. Vegetarian.",
    "pepperoni pizza": "$14 - Topped with premium pepperoni slices.",
    "bbq chicken pizza": "$16 - Smoky BBQ sauce with grilled chicken.",
    "vegetarian pizza": "$13 - Seasonal vegetables and cheese. Vegetarian.",
    "classic beef burger": "$8 - Beef patty with classic condiments.",
    "zinger burger": "$7 - Crispy fried chicken with spicy sauce.",
    "double cheese burger": "$10 - Double beef patty and double cheese.",
    "alfredo pasta": "$12 - Creamy white sauce and parmesan. Vegetarian.",
    "chicken fettuccine": "$13 - Fettuccine ribbons with grilled chicken.",
    "lasagna": "$15 - Layered meat lasagna with bechamel.",
    "chicken biryani": "$9 - Aromatic basmati rice with spiced chicken.",
    "chicken karahi": "$18 - Spicy tomato-based wok curry. Spicy.",
    "mutton karahi": "$25 - Slow-cooked mutton in karahi. Spicy.",
    "seekh kebab": "$10 - Minced meat skewer served with chutney.",
    "chicken manchurian": "$14 - Crispy chicken in Manchurian sauce. Spicy.",
    "chicken chow mein": "$12 - Stir-fried noodles with vegetables.",
    "fried rice": "$10 - Egg fried rice with vegetables.",
    "chocolate lava cake": "$6 - Warm cake with molten chocolate centre.",
    "brownie with ice cream": "$7 - Fudge brownie topped with vanilla ice cream.",
    "cheesecake": "$8 - New York style, served chilled.",
    "coca cola": "$2 - Regular / Diet.",
    "fresh lime": "$3 - Freshly squeezed lime with mint.",
    "mint margarita": "$4 - Blended mint, lime, and soda.",
    "coffee": "$3 - Hot brewed coffee.",
}


def normalize_question(question: str) -> str:
    question = question.lower().strip()
    replacements = {
        "muton": "mutton",
        "moton": "mutton",
        "muttonn": "mutton",
        "karahhai": "karahi",
        "orice": "price",
        "prize": "price",
        "rate": "price",
        "rates": "price",
        "timing": "hours",
        "timings": "hours",
        "application": "app",
    }
    for wrong, right in replacements.items():
        question = question.replace(wrong, right)
    return question


def deterministic_answer(question: str) -> Optional[str]:
    q = normalize_question(question)

    if q in {"hi", "hello", "hey", "salam", "assalamualaikum", "assalamu alaikum"}:
        return "Hello! Ask me anything about the Bella Vista Restaurant knowledge base."

    for item, details in MENU_ITEMS.items():
        if item in q:
            return f"{item.title()}: {details}"

    if "mutton" in q:
        return f"Mutton Karahi: {MENU_ITEMS['mutton karahi']}"

    if "hours" in q or "open" in q or "close" in q:
        return "Bella Vista is open Monday to Thursday from 11:00 AM to 11:00 PM, Friday to Sunday from 11:00 AM to 12:00 AM, and public holidays from 10:00 AM to 1:00 AM."

    if "vegetarian" in q:
        return "Vegetarian dishes include Margherita Pizza, Vegetarian Pizza, and Alfredo Pasta."

    if "delivery" in q or "deliver" in q:
        return "Delivery is available within 20 km. It usually takes 30 to 45 minutes and costs $2, with free delivery above $30."

    if "reservation" in q or "reserve" in q or "booking" in q:
        return "Reservations are free. You can reserve online at www.bellavista.com or by calling +92-300-1234567."

    if "refund" in q or "wrong order" in q or "wrong item" in q:
        return "Refunds are handled through customer support based on the issue, such as wrong item, late delivery, or food quality problem."

    if "loyalty" in q or "gold" in q or "platinum" in q or "silver" in q:
        return "Bella Vista loyalty tiers are Silver 5%, Gold 10%, and Platinum 15% discounts."

    if "catering" in q or "cater" in q:
        return "Bella Vista caters weddings, corporate events, and birthday parties. Minimum guests are 50 and maximum capacity is 1,000."

    if "wifi" in q or "wi-fi" in q:
        return "Yes. All three branches offer free WiFi for dine-in customers."

    if "halal" in q:
        return "Yes. All meat served at Bella Vista is 100% halal-certified."

    if "parking" in q:
        return "Yes. All three branches have dedicated parking. Clifton and DHA branches have valet parking on weekends."

    return None


@st.cache_data(show_spinner=False)
def load_pdf_text() -> str:
    reader = PdfReader(str(PDF_PATH))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_keywords(text: str) -> set[str]:
    stop_words = {
        "what", "when", "where", "who", "how", "is", "are", "the", "a", "an",
        "do", "does", "of", "to", "for", "about", "tell", "me", "bella", "vista",
        "restaurant", "can", "you", "please", "give", "and", "in", "on", "from",
        "with", "without", "any", "thing", "anything",
    }
    words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return {word for word in words if word not in stop_words and len(word) > 2}


def retrieve_context(question: str, text: str, limit: int = 6) -> str:
    keywords = get_keywords(question)
    if not keywords:
        return ""

    segments = re.split(r"(?=Q:\s)|(?=»\s)|(?=\d+\.\s+[A-Z])|(?<=[.!?])\s+", clean_text(text))
    scored_segments = []

    for segment in segments:
        segment_keywords = get_keywords(segment)
        score = len(keywords & segment_keywords)
        if score > 0:
            scored_segments.append((score, segment))

    scored_segments.sort(reverse=True, key=lambda item: item[0])
    return "\n\n".join(segment for _, segment in scored_segments[:limit])


def local_answer(question: str, context: str) -> str:
    if not context:
        return NOT_FOUND_MESSAGE

    sentences = re.split(r"(?<=[.!?])\s+", context)
    scored_sentences = []
    keywords = get_keywords(question)

    for sentence in sentences:
        score = len(keywords & get_keywords(sentence))
        if score > 0:
            scored_sentences.append((score, sentence.strip()))

    if not scored_sentences:
        return NOT_FOUND_MESSAGE

    scored_sentences.sort(reverse=True, key=lambda item: item[0])
    return " ".join(sentence for _, sentence in scored_sentences[:3])


def groq_answer(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return local_answer(question, context)

    prompt = f"""
You are the Bella Vista Restaurant Knowledge Base assistant.
Answer using only the context below.
If the answer is not in the context, say: "{NOT_FOUND_MESSAGE}"

Context:
{context}

Question:
{question}

Answer:
"""
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def answer_question(question: str) -> str:
    direct_answer = deterministic_answer(question)
    if direct_answer:
        return direct_answer

    pdf_text = load_pdf_text()
    context = retrieve_context(question, pdf_text)
    if not context:
        return NOT_FOUND_MESSAGE

    try:
        return groq_answer(question, context)
    except Exception:
        return local_answer(question, context)


st.title("Bella Vista Restaurant Chatbot")
st.caption("Ask questions from the Bella Vista restaurant knowledge base.")

with st.sidebar:
    st.header("Knowledge Base")
    st.write("PDF: Bella Vista Restaurant Knowledge Base")
    st.write("Answers come from the preloaded restaurant document.")
    st.divider()
    st.write("For Streamlit Cloud, add `GROQ_API_KEY` in app secrets.")


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to Bella Vista. Ask about menu items, hours, delivery, "
                "reservations, refunds, loyalty, or catering."
            ),
        }
    ]


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


prompt = st.chat_input("Ask about hours, menu prices, delivery, reservations...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            answer = answer_question(prompt)
            st.write(answer)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
        except Exception as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            error_message = f"Backend error: {detail}"
            st.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
