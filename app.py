import streamlit as st
import os
import sys
import time
import uuid
from typing import List
import pypdf
from openai import OpenAI

# Force local import of ksdb
sys.path.insert(0, os.path.abspath("."))

from ksdb.client import Client

# --- Configuration ---
st.set_page_config(page_title="KSdb RAG Demo", layout="wide")

# Initialize KSdb Client
@st.cache_resource
def get_ksdb_client():
    return Client(url="http://127.0.0.1:8000")

try:
    client = get_ksdb_client()
    collection = client.get_or_create_collection("rag_demo")
except Exception as e:
    st.error(f"Failed to connect to KSdb: {e}. Make sure server is running!")
    st.stop()

# Initialize LLM Client
if "HF_TOKEN" not in os.environ:
    st.error("⚠️ Please set HF_TOKEN environment variable")
    st.stop()

llm_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

# Use Qwen 2.5 72B (Reliable & Fast)
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"

# --- Sidebar: Data Ingestion ---
with st.sidebar:
    st.header("📚 Add Knowledge")
    uploaded_files = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"], accept_multiple_files=True)
    
    if uploaded_files and st.button("Process & Ingest"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            status_text.text(f"Processing {file.name}...")
            text = ""
            
            if file.type == "application/pdf":
                try:
                    pdf_reader = pypdf.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                except Exception as e:
                    st.error(f"Error reading PDF: {e}")
                    continue
            else:
                text = file.read().decode("utf-8")
            
            if not text.strip() or len(text) < 50:
                st.warning(f"⚠️ Low text detected ({len(text)} chars). Attempting OCR (Optical Character Recognition)...")
                st.caption("This might take a moment as we read the images...")
                
                try:
                    import pypdfium2 as pdfium
                    import easyocr
                    import numpy as np
                    
                    # Initialize EasyOCR (English) - loads model once
                    if 'ocr_reader' not in st.session_state:
                         st.session_state.ocr_reader = easyocr.Reader(['en'], gpu=False) # Force CPU for compatibility if needed, or True if confident
                    
                    reader = st.session_state.ocr_reader
                    
                    # Reset file pointer
                    file.seek(0)
                    pdf_file = pdfium.PdfDocument(file)
                    
                    ocr_text = ""
                    progress_text = st.empty()
                    
                    for page_idx, page in enumerate(pdf_file):
                        progress_text.text(f"Scanning page {page_idx+1}/{len(pdf_file)}...")
                        # Render page to image
                        bitmap = page.render(scale=2) # 2x scale for better quality
                        pil_image = bitmap.to_pil()
                        img_array = np.array(pil_image)
                        
                        # Run OCR
                        results = reader.readtext(img_array, detail=0)
                        ocr_text += " ".join(results) + "\n\n"
                        
                    text = ocr_text
                    st.success(f"✅ OCR Complete! Extracted {len(text)} characters.")
                    
                except ImportError:
                    st.error("OCR libraries not found. Please install: `pip install easyocr pypdfium2`")
                except Exception as e:
                    st.error(f"OCR Failed: {e}")
            
            if not text.strip():
                st.error(f"⚠️ No text found in {file.name}! Is it a scanned image?")
                continue
            
            # Simple Chunking (Paragraphs)
            chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 50]
            
            if not chunks:
                st.warning(f"⚠️ Text too short or no paragraphs found in {file.name}. Trying line-based chunking...")
                chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 50]
            
            if chunks:
                st.caption(f"🧩 Created {len(chunks)} chunks")
                ids = [str(uuid.uuid4()) for _ in chunks]
                metadatas = [{"source": file.name, "chunk": j} for j in range(len(chunks))]
                
                # Add to KSdb with Auto-Extraction & Deduplication
                collection.add(
                    ids=ids,
                    documents=chunks,
                    metadatas=metadatas,
                    deduplicate=True,
                    extract_graph=True
                )
            else:
                st.error(f"❌ Could not create any chunks from {file.name}")
            
            progress_bar.progress((i + 1) / total_files)
            
        status_text.success(f"✅ Ingested {total_files} files!")
        time.sleep(2)
        status_text.empty()
        progress_bar.empty()

    st.divider()
    st.subheader("📊 Collection Stats")
    if st.button("Refresh Stats"):
        # We don't have a count method exposed in client yet, but we can list collections
        cols = client.list_collections()
        st.write(cols)

# --- Main Chat Interface ---
st.title("🧠 KSdb RAG Chat")
st.caption("Powered by KSdb (Hybrid Search + Knowledge Graph) & Nebius LLM")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something about your documents..."):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Retrieval & Generation
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            with st.spinner("Generating response..."):
                # A. Search KSdb
                start_time = time.time()
                results = collection.query(
                    query_texts=[prompt],
                    n_results=5
                )
                
                retrieval_time = time.time() - start_time
                
                # Prepare Context
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                
                context_text = "\n\n".join([f"[Source: {m.get('source', 'unknown')}]\n{d}" for d, m in zip(documents, metadatas)])
                
                # C. Generate Answer
                gen_start_time = time.time()
                
                system_prompt = """You are an expert Customer Support Agent for a premium service. 
                Your goal is to provide accurate, helpful, and delightful assistance based strictly on the provided knowledge base.

                Tone & Style:
                - Warm, professional, and empathetic.
                - Clear and concise, avoiding jargon where possible.
                - Use bullet points for lists to improve readability.

                Instructions:
                1. Start with a brief, friendly acknowledgement if appropriate.
                2. STRICTLY use the provided 'Context' to answer the user's question.
                3. If the answer is found, explain it clearly.
                4. If the answer is NOT in the context, politely apologize and state: "I'm sorry, but I couldn't find specific information about that in the documents you've uploaded. Is there anything else I can check for you?"
                5. Do NOT use outside knowledge or make up facts.
                6. End with a helpful closing like "Let me know if you need more details!" or similar."""
                
                completion = llm_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {prompt}"}
                    ],
                )
                
                response = completion.choices[0].message.content
                gen_time = time.time() - gen_start_time
                
                # Display Response
                message_placeholder.markdown(response)
                
                # Display Metrics (Subtle)
                st.caption(f"⏱️ Retrieval: {retrieval_time:.3f}s | Generation: {gen_time:.3f}s")
                
                # Show Sources Expander
                with st.expander("View Sources"):
                    for i, (doc, meta, score) in enumerate(zip(documents, metadatas, distances)):
                        st.markdown(f"**Chunk {i+1}** (Score: {score:.4f})")
                        st.text(doc)
                        st.caption(f"Metadata: {meta}")
                        st.divider()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
