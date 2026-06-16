from pathlib import Path
import shutil

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from embeddings import LocalHashEmbeddings


BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "data" / "Bella_Vista_Restaurant_Knowledge_Base.pdf"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"


def ingest_pdf() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    loader = PyPDFLoader(str(PDF_PATH))
    documents = loader.load()

    if not documents:
        raise ValueError("No text could be loaded from the PDF.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=350,
        chunk_overlap=60,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("No chunks were created from the PDF.")

    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk"] = index

    if VECTORSTORE_DIR.exists():
        shutil.rmtree(VECTORSTORE_DIR)

    embeddings = LocalHashEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTORSTORE_DIR))

    print(f"Ingestion complete. Created {len(chunks)} chunks in {VECTORSTORE_DIR}")


if __name__ == "__main__":
    ingest_pdf()
