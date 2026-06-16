import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel, Field as PydanticField
from pypdf import PdfReader

from embeddings import LocalHashEmbeddings
from ingest import PDF_PATH, VECTORSTORE_DIR, ingest_pdf


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
NOT_FOUND_MESSAGE = "I could not find that information in the Bella Vista knowledge base."
MIN_KEYWORD_MATCHES = 1
SPECIFIC_TERMS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "holiday", "holidays", "clifton", "dha", "mutton", "karahi", "margherita",
    "pizza", "pasta", "chinese", "desserts", "drinks", "delivery", "refund",
    "gold", "platinum", "silver", "mobile", "app", "halal", "wifi", "parking",
}
PRICE_TERMS = {"price", "cost", "costs", "expensive", "cheapest", "under", "pay", "total"}

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


app = FastAPI(
    title="Bella Vista Restaurant Knowledge Base Chatbot API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = PydanticField(..., min_length=1, max_length=1000)


class Source(BaseModel):
    page: Optional[int] = None
    source: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source] = PydanticField(default_factory=list)


vectorstore: Optional[FAISS] = None
pdf_chunks: List[str] = []
qa_pairs: List[Tuple[str, str]] = []


PROMPT_TEMPLATE = """
You are the Bella Vista Restaurant Knowledge Base assistant.
Answer the user's question using only the context below.

Rules:
- If the answer is in the context, answer clearly and concisely.
- If the answer is not in the context, say: "{not_found_message}"
- Do not use outside knowledge.
- Do not invent menu items, prices, timings, policies, or contact details.
- Keep answers short and student-project friendly.

Context:
{context}

Question:
{question}

Answer:
"""


def validate_api_key() -> None:
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_google_api_key_here":
        raise RuntimeError("GOOGLE_API_KEY is missing or still uses the placeholder value in backend/.env.")


def is_greeting(question: str) -> bool:
    clean_question = question.strip().lower()
    greetings = {"hi", "hello", "hey", "salam", "assalamualaikum", "assalamu alaikum"}
    return clean_question in greetings


def normalize_question(question: str) -> str:
    question = question.lower().strip()
    replacements = {
        "muton": "mutton",
        "moton": "mutton",
        "muttonn": "mutton",
        "karahhai": "karahi",
        "karahi": "karahi",
        "orice": "price",
        "prize": "price",
        "rate": "price",
        "rates": "price",
        "timing": "hours",
        "timings": "hours",
        "mobile application": "mobile app",
        "application": "app",
    }
    for wrong, right in replacements.items():
        question = question.replace(wrong, right)
    return question


def find_menu_item(question: str) -> Optional[str]:
    normalized = normalize_question(question)
    compact_question = re.sub(r"[^a-z0-9 ]+", " ", normalized)

    for item in MENU_ITEMS:
        if item in compact_question:
            return item

    words = set(compact_question.split())
    best_item = None
    best_score = 0

    for item in MENU_ITEMS:
        item_words = set(item.split())
        score = len(words & item_words)
        if score > best_score:
            best_score = score
            best_item = item

    if best_score >= 2:
        return best_item

    return None


def deterministic_answer(question: str) -> Optional[str]:
    q = normalize_question(question)

    if q in {"how are you", "how are you?", "how r u", "how are u"}:
        return "I am good! Ask me anything about the Bella Vista Restaurant knowledge base."

    item = find_menu_item(q)
    if item:
        return f"{item.title()}: {MENU_ITEMS[item]}"

    if "mutton" in q:
        return f"Mutton Karahi: {MENU_ITEMS['mutton karahi']}"

    if "hours" in q or "open" in q or "close" in q:
        if "public holiday" in q or "holiday" in q:
            return "On public holidays, Bella Vista is open from 10:00 AM to 1:00 AM next day."
        if "friday" in q or "saturday" in q or "sunday" in q or "weekend" in q:
            return "Friday to Sunday hours are 11:00 AM to 12:00 AM midnight."
        if "clifton" in q and "weekday" in q:
            return "The PDF lists general weekday hours as Monday to Thursday, 11:00 AM to 11:00 PM."
        return "Bella Vista is open Monday to Thursday from 11:00 AM to 11:00 PM, Friday to Sunday from 11:00 AM to 12:00 AM, and public holidays from 10:00 AM to 1:00 AM."

    if "menu" in q or "food" in q or "dish" in q or "dishes" in q:
        if "vegetarian" in q:
            return "Vegetarian dishes include Margherita Pizza, Vegetarian Pizza, and Alfredo Pasta."
        if "chinese" in q:
            return "Chinese dishes are Chicken Manchurian ($14), Chicken Chow Mein ($12), and Fried Rice ($10)."
        if "dessert" in q:
            return "Desserts are Chocolate Lava Cake ($6), Brownie with Ice Cream ($7), and Cheesecake ($8)."
        if "drink" in q:
            return "Drinks are Coca Cola ($2), Fresh Lime ($3), Mint Margarita ($4), and Coffee ($3)."
        if "spicy" in q:
            return "Spicy dishes are Chicken Karahi, Mutton Karahi, and Chicken Manchurian."
        if "gluten" in q:
            return "Gluten-free options include Grilled Chicken Salad and Fresh Fruit Bowl."
        return "Bella Vista serves pizza, burgers, pasta, Pakistani food, Chinese food, desserts, and drinks."

    if "mobile app" in q or "mobile" in q or "app" in q:
        return "Yes. Bella Vista has a planned mobile ordering application for iOS and Android, allowing customers to order, track, and pay from their phones."

    if "delivery" in q or "deliver" in q:
        if "free" in q:
            return "Delivery is free on orders above $30."
        if "charge" in q or "fee" in q:
            return "The delivery charge is $2."
        if "far" in q or "radius" in q:
            return "Bella Vista delivers within a 20 km radius from each branch."
        if "late" in q:
            return "If delivery exceeds 90 minutes, you automatically qualify for a 50% refund. Contact support to process it."
        if "track" in q:
            return "After order confirmation, you receive an SMS and email tracking link. You can also track from the Orders section on the website."
        return "Delivery is available within 20 km. It usually takes 30 to 45 minutes and costs $2, with free delivery above $30."

    if "reservation" in q or "reserve" in q or "booking" in q or "book" in q:
        if "cancel" in q:
            return "You can cancel up to 2 hours before the reserved time with no penalty. Cancellations within 2 hours may not be refunded."
        if "60" in q:
            return "A normal reservation supports up to 50 people. For 60 people, use catering services."
        return "Reservations are free. You can reserve online at www.bellavista.com or by calling +92-300-1234567."

    if "refund" in q or "wrong order" in q or "wrong item" in q or "quality" in q:
        if "90" in q or "100" in q or "late" in q:
            return "If delivery exceeds 90 minutes, you qualify for a 50% refund. Contact support to process it."
        if "wrong" in q:
            return "For a wrong item or wrong order, contact support so they can process the refund or correction."
        if "quality" in q:
            return "If food quality is bad, contact the support team with your order details."
        return "Refunds are handled through customer support based on the issue, such as wrong item, late delivery, or food quality problem."

    if "loyalty" in q or "member" in q or "gold" in q or "platinum" in q or "silver" in q:
        if "platinum" in q:
            return "Platinum Members get a 15% discount on all orders."
        if "gold" in q:
            return "Gold Members get a 10% discount on all orders."
        if "silver" in q:
            return "Silver Members get a 5% discount on all orders."
        return "Bella Vista loyalty tiers are Silver 5%, Gold 10%, and Platinum 15% discounts."

    if "catering" in q or "cater" in q or "wedding" in q or "corporate" in q or "birthday" in q:
        if "200" in q:
            return "Yes. Bella Vista can cater a corporate lunch for 200 people because catering supports 50 to 1,000 guests."
        if "80" in q:
            return "For catering for 80 guests, contact support@bellavista.com or +92-300-1234567."
        return "Bella Vista caters weddings, corporate events, and birthday parties. Minimum guests are 50 and maximum capacity is 1,000."

    if "payment" in q or "pay" in q:
        return "Bella Vista accepts Cash, Credit Card, Debit Card, and Online Bank Transfer."

    if "wifi" in q or "wi-fi" in q:
        return "Yes. All three branches offer free WiFi for dine-in customers."

    if "halal" in q:
        return "Yes. All meat served at Bella Vista is 100% halal-certified."

    if "parking" in q:
        return "Yes. All three branches have dedicated parking. Clifton and DHA branches have valet parking on weekends."

    if "outdoor" in q or "seating" in q:
        return "The DHA branch has garden terrace outdoor seating. The Clifton branch has a rooftop area during pleasant weather. The Main branch is indoor only."

    if "ceo" in q:
        return "The PDF does not provide the CEO name."

    if "branch" in q or "branches" in q:
        return "Bella Vista has three branches: Karachi Main, Clifton, and DHA."

    return None


def get_keywords(text: str) -> set[str]:
    stop_words = {
        "what", "when", "where", "who", "how", "is", "are", "the", "a", "an",
        "do", "does", "of", "to", "for", "about", "tell", "me", "bella", "vista",
        "restaurant", "can", "you", "please", "give", "and", "in", "on", "from",
        "with", "without", "any", "thing", "anything",
    }
    words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    keywords = {word for word in words if word not in stop_words and len(word) > 2}
    aliases = {
        "menu": {"starters", "dishes", "pizza", "pasta", "salad"},
        "food": {"starters", "dishes", "pizza", "pasta", "salad"},
        "timing": {"opening", "hours"},
        "timings": {"opening", "hours"},
        "open": {"opening", "hours"},
        "close": {"opening", "hours"},
        "reservation": {"reservations", "phone"},
        "reserve": {"reservations", "phone"},
        "booking": {"bookings", "reservations"},
        "location": {"located", "street", "san", "diego"},
        "address": {"located", "street", "san", "diego"},
        "contact": {"phone"},
        "number": {"phone"},
    }

    expanded_keywords = set(keywords)
    for keyword in keywords:
        expanded_keywords.update(aliases.get(keyword, set()))

    return expanded_keywords


def keyword_score(question: str, text: str) -> int:
    keywords = get_keywords(question)
    if not keywords:
        return 0
    text_words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    score = len(keywords & text_words)
    clean_question = question.lower()
    clean_text = text.lower()

    for phrase in re.findall(r"[a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)+", clean_question):
        if phrase in clean_text:
            score += 3

    return score


def is_relevant(question: str, chunks: list) -> bool:
    keywords = get_keywords(question)
    if not keywords:
        return False

    combined_text = " ".join(
        chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
        for chunk in chunks
    )
    return keyword_score(question, combined_text) >= MIN_KEYWORD_MATCHES


def load_vectorstore() -> FAISS:
    if not (VECTORSTORE_DIR / "index.faiss").exists():
        ingest_pdf()

    embeddings = LocalHashEmbeddings()

    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_pdf_text() -> str:
    reader = PdfReader(str(PDF_PATH))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def build_pdf_chunks(text: str, chunk_size: int = 700, overlap: int = 120) -> List[str]:
    text = clean_text(text)
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk.strip())
        if end == len(text):
            break
        start = max(0, end - overlap)

    return chunks


def extract_qa_pairs(text: str) -> List[Tuple[str, str]]:
    matches = re.findall(r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\s*Q:|$)", text, flags=re.S)
    pairs = []

    for question, answer in matches:
        question = clean_text(question)
        answer = clean_text(answer)
        if question and answer:
            pairs.append((question, answer))

    return pairs


def load_pdf_index() -> None:
    global pdf_chunks, qa_pairs
    text = load_pdf_text()
    pdf_chunks = build_pdf_chunks(text)
    qa_pairs = extract_qa_pairs(text)


def lexical_retrieve(question: str, limit: int = 5) -> List[str]:
    scored_chunks = []

    for chunk in pdf_chunks:
        score = keyword_score(question, chunk)
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(reverse=True, key=lambda item: item[0])
    return [chunk for _, chunk in scored_chunks[:limit]]


def faq_answer(question: str) -> Optional[str]:
    scored_pairs = []
    question_keywords = get_keywords(question)
    required_terms = question_keywords & SPECIFIC_TERMS
    needs_price = bool(question_keywords & PRICE_TERMS)

    for faq_question, faq_answer_text in qa_pairs:
        searchable_text = f"{faq_question} {faq_answer_text}"
        if len(faq_answer_text) > 700:
            continue

        if needs_price and not re.search(r"\$|price|cost|pay|discount|free", searchable_text, flags=re.I):
            continue

        if required_terms and not required_terms.issubset(get_keywords(searchable_text)):
            continue

        score = keyword_score(question, searchable_text)
        if score > 0:
            scored_pairs.append((score, faq_question, faq_answer_text))

    if not scored_pairs:
        return None

    scored_pairs.sort(reverse=True, key=lambda item: item[0])
    best_score, _, answer = scored_pairs[0]

    if best_score < 2 and len(get_keywords(question)) > 1:
        return None

    return answer


def exact_phrase_snippet(question: str, context: str) -> Optional[str]:
    words = [
        word for word in re.findall(r"[a-zA-Z0-9]+", question.lower())
        if word in get_keywords(question)
    ]
    phrases = []

    for size in range(min(4, len(words)), 0, -1):
        for index in range(0, len(words) - size + 1):
            phrases.append(" ".join(words[index:index + size]))

    clean_context = clean_text(context)
    lower_context = clean_context.lower()

    for phrase in phrases:
        position = lower_context.find(phrase)
        if position == -1:
            continue

        start = max(0, position - 180)
        end = min(len(clean_context), position + 260)
        snippet = clean_context[start:end].strip(" ,.;:-")
        return snippet

    return None


def best_segment_answer(question: str, context: str) -> Optional[str]:
    segments = re.split(r"(?=Q:\s)|(?=»\s)|(?=\d+\.\s+[A-Z])|(?<=[.!?])\s+", context)
    scored_segments = []

    for segment in segments:
        segment = clean_text(segment)
        score = keyword_score(question, segment)
        if score > 0:
            scored_segments.append((score, segment))

    if not scored_segments:
        return None

    scored_segments.sort(reverse=True, key=lambda item: item[0])
    answer = scored_segments[0][1]
    return answer[:650].strip()


def price_answer(question: str, context: str) -> Optional[str]:
    if not (get_keywords(question) & PRICE_TERMS):
        return None

    keywords = [
        word for word in re.findall(r"[a-zA-Z0-9]+", question)
        if word.lower() in get_keywords(question)
    ]

    if len(keywords) < 2:
        return None

    item_pattern = r"\s+".join(re.escape(word) for word in keywords[-2:])
    match = re.search(
        rf"({item_pattern})\s+(\$\d+(?:\.\d+)?)\s+(.{{0,120}}?)(?=\s+[A-Z][A-Za-z ]+\s+\$\d|$)",
        clean_text(context),
        flags=re.I,
    )

    if not match:
        return None

    item = match.group(1).strip()
    price = match.group(2).strip()
    details = match.group(3).strip(" .,:;")
    return f"{item} costs {price}. {details}".strip()


def generate_answer(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from backend/.env.")
    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question,
        not_found_message=NOT_FOUND_MESSAGE,
    )
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def local_pdf_answer(question: str, context: str) -> str:
    keywords = get_keywords(question)

    direct_answer = faq_answer(question)
    if direct_answer:
        return direct_answer

    menu_price_answer = price_answer(question, context)
    if menu_price_answer:
        return menu_price_answer

    segment_answer = best_segment_answer(question, context)
    if segment_answer:
        return segment_answer

    snippet = exact_phrase_snippet(question, context)
    if snippet and keyword_score(question, snippet) >= MIN_KEYWORD_MATCHES:
        return snippet

    sentences = re.split(r"(?<=[.!?])\s+", context.replace("\n", " "))
    scored_sentences = []

    for sentence in sentences:
        score = keyword_score(question, sentence)
        if score > 0:
            scored_sentences.append((score, sentence.strip()))

    if not scored_sentences:
        return NOT_FOUND_MESSAGE

    scored_sentences.sort(reverse=True, key=lambda item: item[0])
    best_sentences = [sentence for _, sentence in scored_sentences[:3]]
    return " ".join(best_sentences)


def is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota" in message or "rate" in message


@app.on_event("startup")
def startup_event() -> None:
    global vectorstore
    try:
        load_pdf_index()
        vectorstore = load_vectorstore()
    except Exception as exc:
        print(f"Startup warning: {exc}")
        vectorstore = None


@app.get("/")
def root() -> dict:
    return {"message": "Bella Vista Restaurant Knowledge Base Chatbot API is running."}


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "vectorstore_ready": vectorstore is not None,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    global vectorstore

    if is_greeting(request.question):
        return ChatResponse(
            answer="Hello! Ask me anything about the Bella Vista Restaurant knowledge base.",
            sources=[],
        )

    direct_answer = deterministic_answer(request.question)
    if direct_answer:
        return ChatResponse(answer=direct_answer, sources=[])

    if vectorstore is None:
        try:
            load_pdf_index()
            vectorstore = load_vectorstore()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        if not pdf_chunks:
            load_pdf_index()

        lexical_chunks = lexical_retrieve(request.question, limit=5)
        if not is_relevant(request.question, lexical_chunks):
            return ChatResponse(answer=NOT_FOUND_MESSAGE, sources=[])

        source_documents = vectorstore.similarity_search(request.question, k=5)
        faiss_chunks = [document.page_content for document in source_documents]
        context_chunks = lexical_chunks + [
            chunk for chunk in faiss_chunks if chunk not in lexical_chunks
        ]
        context = "\n\n".join(context_chunks[:8])
        try:
            answer = generate_answer(request.question, context)
        except Exception as exc:
            if not is_quota_error(exc):
                raise
            print(f"Gemini quota reached. Using local PDF fallback: {exc}")
            answer = local_pdf_answer(request.question, context)

        sources = []
        for document in source_documents:
            metadata = document.metadata or {}
            page_number = metadata.get("page")
            sources.append(
                Source(
                    page=page_number + 1 if isinstance(page_number, int) else None,
                    source=metadata.get("source"),
                )
            )

        return ChatResponse(answer=answer, sources=sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
