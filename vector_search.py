import torch
from sentence_transformers import SentenceTransformer, util
import chromadb

# Connect to ChromaDB persistent client
client = chromadb.PersistentClient(path="chroma_db/")
import torch
from sentence_transformers import SentenceTransformer, util
import chromadb

# Connect to ChromaDB persistent client
client = chromadb.PersistentClient(path="chroma_db/")

# FIX: Use get_or_create_collection instead of get_collection to avoid NotFoundError
collection = client.get_or_create_collection("my_chunks") 

embedding_model = SentenceTransformer("all-mpnet-base-v2")

RELEVANCE_THRESHOLD = 0.05

def retrieve_relevant_chunks(query, top_k=5):
    print(f"\n[DEBUG] Query: {query}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    query_embedding = embedding_model.encode(query, convert_to_tensor=True).to(device)

    # Query ChromaDB for candidate chunks
    results = collection.query(
        query_embeddings=[query_embedding.cpu().numpy().tolist()],
        n_results=top_k,
        include=["documents", "embeddings", "metadatas"]
    )

    ret_embeddings = torch.tensor(results["embeddings"][0], dtype=torch.float32).to(device)
    ret_documents = results["documents"][0]
    ret_metadatas = results["metadatas"][0]

    # Compute dot product scores just like before
    scores = util.dot_score(query_embedding, ret_embeddings)[0]

    results_list = []
    for j, (score, doc, meta) in enumerate(zip(scores, ret_documents, ret_metadatas)):
        s = float(score)
        if s >= RELEVANCE_THRESHOLD:
            print(f"[DEBUG] Retrieved Chunk {j+1}: {doc[:100]}... (score: {s:.4f})")
            row = meta.copy()
            row["sentence_chunk"] = doc
            results_list.append((row, s))

    return results_list
