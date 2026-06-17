# Bella Vista Restaurant RAG Chatbot

A simple course-level RAG chatbot. It reads one PDF from the backend `data` folder, stores it in FAISS with local embeddings, and answers questions through a FastAPI API and React chat UI.

## Project Structure

```text
project-root/
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
├── backend/
│   ├── data/
│   │   └── Bella_Vista_Restaurant_Knowledge_Base.pdf
│   ├── vectorstore/
│   ├── app.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
└── README.md
```

## Backend Setup

## Run With One Command

From the project root:

```bash
bash start.sh
```

Open:

```text
http://localhost:5173
```

The script starts both backend and frontend in one terminal.

## Manual Backend Setup

1. Go to the backend folder:

```bash
cd backend
```

2. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Add your Groq API key in `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

5. Build the FAISS vector database:

```bash
python3 ingest.py
```

6. Start the API:

```bash
uvicorn app:app --reload
```

The backend runs at `http://localhost:8000`.

## Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

## API

### POST `/chat`

Request:

```json
{
  "question": "What are the restaurant opening hours?"
}
```

Response:

```json
{
  "answer": "Bella Vista is open Monday through Thursday from 11:00 AM to 10:00 PM...",
  "sources": [
    {
      "page": 1,
      "source": "backend/data/Bella_Vista_Restaurant_Knowledge_Base.pdf"
    }
  ]
}
```

## Notes

- There is no PDF upload option in the UI.
- The backend always uses the preloaded PDF from `backend/data`.
- Run `python3 ingest.py` once before chatting.
- The assistant answers only from the PDF context.

## Deployment Notes

- Deploy the React frontend from the `frontend` folder.
- Deploy the FastAPI backend from the `backend` folder with start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

- Set `GROQ_API_KEY` in the backend deploy environment.
- Set `VITE_API_URL` in the frontend deploy environment to your deployed backend URL.
# bella-vista-chatbot
# New-bella-vista-chatbot
