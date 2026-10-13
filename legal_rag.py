import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from checklist import split_clauses

COLLECTION = "contract_collection"
PERSIST_DIR = "./legal_vector_db"

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# Shared state: the currently loaded contract (used by the tools and the UI)
STATE = {"name": None, "clauses": [], "store": None}


def load_text(path: str) -> str:
    """Load a PDF or TXT contract and return its full text."""
    if path.lower().endswith(".pdf"):
        pages = PyPDFLoader(path).load()
    else:
        pages = TextLoader(path, encoding="utf-8").load()
    return "\n".join(p.page_content for p in pages)


def build_chunks(text: str, source: str):
    """Split by numbered clause. If the contract has no numbering, fall back
    to a normal character splitter so the app never crashes."""
    clauses = split_clauses(text)
    if not clauses:
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        clauses = [
            {"number": i + 1, "title": f"Section {i + 1}", "text": chunk}
            for i, chunk in enumerate(splitter.split_text(text))
        ]
    docs = [
        Document(
            page_content=c["text"],
            metadata={"clause_no": c["number"], "title": c["title"], "source": source},
        )
        for c in clauses
    ]
    return clauses, docs


def load_contract(path: str) -> str:
    """Load, split, embed and index one contract. Replaces any previous one."""
    text = load_text(path)
    name = os.path.basename(path)
    clauses, docs = build_chunks(text, name)

    # start fresh so an old contract never leaks into new answers
    try:
        Chroma(collection_name=COLLECTION, embedding_function=embeddings,
               persist_directory=PERSIST_DIR).delete_collection()
    except Exception:
        pass

    store = Chroma.from_documents(
        docs, embedding=embeddings,
        collection_name=COLLECTION, persist_directory=PERSIST_DIR,
    )
    STATE.update(name=name, clauses=clauses, store=store)
    return f"Loaded '{name}': {len(clauses)} clauses indexed."


def retrieve_clauses(query: str, k: int = 3) -> str:
    """Return the k most relevant clauses, each labelled with its clause number."""
    if STATE["store"] is None:
        return "No contract is loaded yet. Ask the user to upload one first."
    docs = STATE["store"].similarity_search(query, k=k)
    if not docs:
        return "No matching clause found in this contract."
    parts = []
    for d in docs:
        parts.append(f"[Clause {d.metadata['clause_no']}: {d.metadata['title']}]\n{d.page_content}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    print(load_contract("sample_contracts/sample_nda.txt"))
    print(retrieve_clauses("What is the termination notice period?"))
