import os
import fitz  # PyMuPDF
import re
from tqdm import tqdm
from spacy.lang.en import English
from sentence_transformers import SentenceTransformer
import chromadb
from docx import Document

# Initialize models
nlp = English()
nlp.add_pipe("sentencizer")
embedding_model = SentenceTransformer("all-mpnet-base-v2")

def process_and_index_files(file_paths, db_path="chroma_db/"):
    """Extracts text, creates embeddings, and stores them in ChromaDB."""
    print(f"[PROCESSOR] Starting processing for {len(file_paths)} files...")
    
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection("my_chunks")
    
    all_chunks = []
    
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        text = ""

        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            text = " ".join([page.get_text() for page in doc])
        
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            text = " ".join([para.text for para in doc.paragraphs])
            
        elif file_path.lower().endswith((".txt", ".md")):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            print(f"Skipping unsupported format: {file_name}")
            continue
            
        try:
            doc = fitz.open(file_path)
            file_name = os.path.basename(file_path)
            
            for page_num, page in enumerate(doc):
                text = page.get_text().replace("\n", " ").strip()
                sentences = [str(s) for s in nlp(text).sents]
                
                for i in range(0, len(sentences), 10):
                    chunk_text = " ".join(sentences[i:i+10])
                    chunk_text = re.sub(r'\.([A-Z])', r'. \1', chunk_text)
                    
                    # Ensure the chunk is long enough to be meaningful
                    if len(chunk_text.split()) > 10: 
                        all_chunks.append({
                            "id": f"{file_name}_{page_num}_{i}",
                            "text": chunk_text,
                            "metadata": {"pdf_file": file_name, "page_number": page_num}
                        })
            doc.close()
        except Exception as e:
            print(f"[PROCESSOR] Error reading {file_path}: {e}")

    if not all_chunks:
        print("[PROCESSOR] No valid text chunks extracted.")
        return "No valid text chunks found."

    print(f"[PROCESSOR] Generating embeddings for {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    ids = [c["id"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    
    # Generate Embeddings
    embeddings = embedding_model.encode(texts).tolist()

    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    print(f"[PROCESSOR] ✅ Indexing complete for {file_name}")
    return f"✅ Successfully indexed {len(all_chunks)} chunks."