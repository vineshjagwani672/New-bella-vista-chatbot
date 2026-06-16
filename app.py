import streamlit as st
import os
from PyPDF2 import PdfReader
import docx

# Text splitting and vector database tools (RAG pipeline)
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Gemini API logic (LLM)
from google import genai
from google.genai import types

# ---------------- Streamlit UI ----------------
# Configure app layout and title
st.set_page_config(page_title="Chat with your files.", layout="wide")
st.title("RAG Chatbot 🤖")

# ---------------- Session State ----------------
# Initialize session variables to persist data across interactions
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None  # Stores embeddings (FAISS DB)

if "messages" not in st.session_state:
    st.session_state.messages = []  # Stores chat history

if "processComplete" not in st.session_state:
    st.session_state.processComplete = False  # Tracks file processing status

# ---------------- Sidebar ----------------
# User input controls
with st.sidebar:
    st.header("⚙️ Settings")

    # Model selection (currently only one option)
    model_name = st.selectbox("Select Model", ["gemini-2.5-flash"])

    # Upload multiple files (PDF or DOCX)
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX", type=["pdf", "docx"], accept_multiple_files=True
    )

    # Input Gemini API key securely
    api_key_input = st.text_input("Enter your Gemini API Key:", type="password")

    # Button to trigger processing pipeline
    process = st.button("Process Files")

# Save API key to session
if api_key_input:
    st.session_state.api_key = api_key_input

# Stop execution if API key is missing
if not hasattr(st.session_state, "api_key") or not st.session_state.api_key:
    st.warning("Please enter your Gemini API key.")
    st.stop()

# Retrieve API key from session
api_key = st.session_state.api_key

# ---------------- File Reading ----------------
# Extract text from uploaded PDF and DOCX files
def get_files_text(files):
    text = ""
    for file in files:
        # Get file extension
        ext = os.path.splitext(file.name)[1].lower()

        if ext == ".pdf":
            # Read PDF file page by page
            pdf = PdfReader(file)
            for page in pdf.pages:
                text += page.extract_text() or ""

        elif ext == ".docx":
            # Read Word document paragraphs
            doc = docx.Document(file)
            text += " ".join([p.text for p in doc.paragraphs])

    return text  # Combined text from all files

# ---------------- Split Text ----------------
# Break large text into smaller chunks for efficient processing
def get_text_chunks(text):
    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=900,      # Max characters per chunk
        chunk_overlap=100    # Overlap for better context continuity
    )
    return splitter.split_text(text)

# ---------------- Vector Store ----------------
# Convert text chunks into embeddings and store in FAISS
def get_vectorstore(chunks):
    # Load embedding model
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Create FAISS vector database from text chunks
    return FAISS.from_texts(chunks, embeddings)

# ---------------- Gemini RAG Call ----------------
# System prompt to control AI behavior
SYSTEM_PROMPT = """
Role: You are an intelligent Document Assistant AI designed to help users understand and interact with their uploaded documents.

You can answer questions using:
1) The provided document context
2) General knowledge (only when needed)

--- Core Behavior ---
- If the question is about the uploaded documents:
  → Answer using ONLY the provided context.
  → Be accurate and specific.

- If the answer is NOT clearly in the document:
  → Say:
    "I couldn't find exact info in the document, but here's a general idea:"
  → Then give a helpful general explanation.

- If the user asks something unrelated to the documents:
  → Respond naturally like a normal chatbot.

--- Conversation Handling ---
- Understand follow-up questions using chat history.
- Answer in a natural conversational tone.
- Handle greetings (hi, hello, etc.) politely.
- Handle unclear questions by asking for clarification.

--- Response Style ---
- Keep answers short, clear, and easy to understand.
- Do NOT assume or infer missing information.
- If something is not explicitly mentioned in the context, do NOT guess.
- Use bullet points when helpful.
- Avoid unnecessary long explanations.
- Do NOT make up information from the document.

--- Special Cases ---
- If user asks to summarize → provide a concise summary from context.
- If multiple topics → organize answer clearly.
- If user input is casual (e.g., "ok", "good") → respond naturally.

--- Priority Order ---
1. Document context (highest priority)
2. Chat history
3. General knowledge (only if needed)

Always be helpful, accurate, and concise.
"""

# Function to generate response using Gemini API
def get_gemini_response(api_key, user_prompt, model_name="gemini-2.5-flash"):
    # Initialize client with API key
    client = genai.Client(api_key=api_key)

    # Generate response using model + system prompt
    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
    )

    return response.text  # Return generated answer

# ---------------- Process Files ----------------
# Triggered when user clicks "Process Files"
if process:
    if not uploaded_files:
        st.warning("Please upload at least one file.")
        st.stop()

    # Step 1: Extract text from files
    files_text = get_files_text(uploaded_files)
    st.success("✅ Files loaded!")

    # Step 2: Split text into chunks
    text_chunks = get_text_chunks(files_text)
    st.success(f"✅ Created {len(text_chunks)} chunks!")

    # Step 3: Convert chunks into embeddings and store in FAISS
    vectorstore = get_vectorstore(text_chunks)

    # Save vector store in session
    st.session_state.vectorstore = vectorstore
    st.session_state.processComplete = True

    st.success("✅ Vector store created!")

# ---------------- Chat ----------------
# Enable chat only after processing is complete
if st.session_state.processComplete:

    # Input box for user query
    user_question = st.chat_input("Ask something about your documents:")

    if user_question:
        # Step 4: Retrieve top relevant chunks using similarity search
        docs = st.session_state.vectorstore.similarity_search(user_question, k=6)

        # Combine retrieved chunks into context
        context = ""
        for i, d in enumerate(docs):
            context += f"[Source {i+1}]:\n{d.page_content}\n\n"
            
        # Create prompt with context + user question
        chat_history = ""
        for msg in st.session_state.messages[-6:]:  # last 3 Q&A
            role = "User" if msg["role"] == "user" else "Assistant"
            chat_history += f"{role}: {msg['content']}\n"

        # New prompt with memory
        user_prompt = f"""
        Chat History:
        {chat_history}

        Context:
        {context}

        Question:
        {user_question}
        """

        try:
            # Step 5: Generate answer using Gemini (RAG)
            answer = get_gemini_response(api_key, user_prompt, model_name)

            # Save chat history
            st.session_state.messages.append({"role": "user", "content": user_question})
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            # Handle API errors
            st.error("Gemini API Error. Check your key or model.")
            st.exception(e)

    # Display full chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])