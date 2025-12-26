import gradio as gr
import hashlib
import os
import traceback
from typing import List, Dict
from prompt_llm import ask
from processor import process_and_index_files 
import markdown

def _get_file_hashes(uploaded_files: List) -> frozenset:
    hashes = set()
    if not uploaded_files:
        return frozenset()

    for file in uploaded_files:
        try:
            if isinstance(file, str) and os.path.exists(file):
                path = file
            elif hasattr(file, "name") and os.path.exists(file.name):
                path = file.name
            elif isinstance(file, dict) and "name" in file and os.path.exists(file["name"]):
                path = file["name"]
            else:
                continue

            with open(path, "rb") as f:
                hashes.add(hashlib.sha256(f.read()).hexdigest())
        except Exception:
            continue

    return frozenset(hashes)

def process_question(question_text: str, uploaded_files: List, state: Dict):
    try:
        if not question_text or not question_text.strip():
            raise ValueError("❌ Question cannot be empty")

        current_hashes = _get_file_hashes(uploaded_files)
        if state is None:
            state = {"file_hashes": frozenset(), "retriever_ready": False}

        # Indexing logic
        if uploaded_files and (not state.get("retriever_ready") or current_hashes != state.get("file_hashes")):
            file_paths = [f.name if hasattr(f, "name") else f for f in uploaded_files]
            process_and_index_files(file_paths)
            state.update({"file_hashes": current_hashes, "retriever_ready": True})

        full_answer_md = ""
        for word in ask(question_text):
            full_answer_md += word
            # Yield the raw markdown string; the UI component will style it
            yield full_answer_md, state
            

    except Exception as e:
        traceback.print_exc()
        # Fallback error box
        error_html = f'<div style="border: 1px solid #ff4b4b; background-color: #fff2f2; padding: 15px; border-radius: 8px; color: #ff4b4b;">❌ Error: {str(e)}</div>'
        yield error_html, state

def main():
    css = """
    .title { font-size: 1.5em !important; text-align: center !important; color: #FFD700; }
    .subtitle { font-size: 1em !important; text-align: center !important; color: #FFD700; }
    .text { text-align: center; }
    """

    # Gradio Animation JS
    js = """
    function createGradioAnimation() {
        var container = document.createElement('div');
        container.id = 'gradio-animation';
        container.style.fontSize = '2em';
        container.style.fontWeight = 'bold';
        container.style.textAlign = 'center';
        container.style.marginBottom = '20px';
        container.style.color = '#eba93f';
        var text = 'Welcome to DocChat 🐥!';
        for (var i = 0; i < text.length; i++) {
            (function(i){
                setTimeout(function(){
                    var letter = document.createElement('span');
                    letter.style.opacity = '0';
                    letter.style.transition = 'opacity 0.1s';
                    letter.innerText = text[i];
                    container.appendChild(letter);
                    setTimeout(function() {
                        letter.style.opacity = '0.9';
                    }, 50);
                }, i * 250);
            })(i);
        }
        var gradioContainer = document.querySelector('.gradio-container');
        if (gradioContainer) gradioContainer.insertBefore(container, gradioContainer.firstChild);
        return 'Animation created';
    }
    """

    allowed_types = [".pdf", ".docx", ".txt", ".md"]

    with gr.Blocks(theme=gr.themes.Citrus(), title="DocChat 🐥", css=css, js=js) as demo:
        gr.Markdown("# 🐥 DocChat", elem_classes="subtitle")
        gr.Markdown("📤 Upload your document(s), enter your query then hit Submit 📝", elem_classes="text")
        gr.Markdown("⚠️ **Note:** Accepted formats: '.pdf', '.docx', '.txt', '.md'", elem_classes="text")

        session_state = gr.State({"file_hashes": frozenset(), "retriever_ready": False})

        with gr.Row():
            with gr.Column():
                files = gr.Files(label="📄 Upload Documents", file_types=allowed_types)
                question = gr.Textbox(label="❓ Question", lines=3)
                submit_btn = gr.Button("Submit 🚀")

            with gr.Column():
    # 'variant="panel"' makes this area look like a standard Gradio input box
                with gr.Column(variant="panel"):
                    gr.Markdown("### 🐥 Answer") 
                    # Markdown renders bullets (* -> dots) and expands as the text grows
                    answer_output = gr.Markdown(value="Your answer will appear here...")

        submit_btn.click(
            fn=process_question,
            inputs=[question, files, session_state],
            outputs=[answer_output, session_state]
        )

    try:
        print("Launching Gradio on http://127.0.0.1:7860 ...")
        demo.launch(server_name="127.0.0.1", server_port=7860, share=False, debug=True)
    except Exception as e:
        print(f"Failed to bind to 127.0.0.1: {e}. Trying 0.0.0.0 with share=True...")
        demo.launch(server_name="0.0.0.0", server_port=7860, share=True, debug=True)

if __name__ == "__main__":
    main()