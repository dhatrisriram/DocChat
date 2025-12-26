import json
import os
import requests
from vector_search import retrieve_relevant_chunks

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

def format_prompt(query, chunks):
    context = "\n".join([f"{i+1}. {item['sentence_chunk']}" for i, (item, _) in enumerate(chunks)])
    return f"""You are a helpful assistant. ONLY use the following internal content to answer the user's question.

### CRITICAL INSTRUCTIONS:
1. **Preserve Detail**: Do not summarize heavily. Use the exact, detailed wording and technical descriptions found in the document chunks.
2. **Structure**: Organize the information into **Bold Headers** for main categories.
3. **Bullet Points**: Use bullet points (*) for primary details and nested bullets (+) for sub-details.
4. **Completeness**: Ensure all relevant facts from the provided context are included in the structured list.

If the answer is not found in this information, reply with:
"I don’t know based on the provided information."

Document Information:
{context}

Question: {query}
Answer:"""

def ask(query):
    # Quick greeting check
    if query.lower().strip() in ["hi", "hello", "hey"]:
        yield "Hello! How can I assist you today?"
        return

    # Retrieval logic (with your updated top_k=10 and lower threshold)
    chunks = retrieve_relevant_chunks(query)
    if not chunks:
        yield "I'm sorry, I couldn't find an answer to that based on the documents."
        return

    prompt = format_prompt(query, chunks)

    try:
        # Enable streaming in the request
        response = requests.post(OLLAMA_URL, json={
            "model": "llama3.1",
            "prompt": prompt,
            "stream": True 
        }, stream=True)
        
        # Process each chunk of the response separately
        for line in response.iter_lines():
            if line:
                body = json.loads(line)
                if "response" in body:
                    yield body["response"]
                if body.get("done"):
                    break
                    
    except Exception as e:
        yield f"[ERROR] Connection failed: {str(e)}"