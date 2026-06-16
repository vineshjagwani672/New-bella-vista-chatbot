#!/bin/bash

echo "Starting Bella Vista RAG Chatbot..."

cd backend || exit
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
if [ ! -f "vectorstore/index.faiss" ]; then
  python3 ingest.py
fi
uvicorn app:app --reload &
BACKEND_PID=$!

cd ../frontend || exit
npm install
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press CTRL+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
