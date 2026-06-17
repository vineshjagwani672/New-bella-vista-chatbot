import os
import sys
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

for secret_name in ("GROQ_API_KEY", "GROQ_MODEL"):
    try:
        if secret_name in st.secrets and not os.getenv(secret_name):
            os.environ[secret_name] = st.secrets[secret_name]
    except Exception:
        pass

from app import ChatRequest, chat  # noqa: E402


st.set_page_config(
    page_title="Bella Vista Chatbot",
    page_icon="BV",
    layout="centered",
)

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
        if message.get("sources"):
            source_pages = [
                f"page {source.page}" for source in message["sources"] if source.page
            ]
            if source_pages:
                st.caption("Source: PDF " + ", ".join(source_pages[:3]))


prompt = st.chat_input("Ask about hours, menu prices, delivery, reservations...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            response = chat(ChatRequest(question=prompt))
            st.write(response.answer)

            if response.sources:
                source_pages = [
                    f"page {source.page}" for source in response.sources if source.page
                ]
                if source_pages:
                    st.caption("Source: PDF " + ", ".join(source_pages[:3]))

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response.answer,
                    "sources": response.sources,
                }
            )
        except Exception as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            error_message = f"Backend error: {detail}"
            st.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
