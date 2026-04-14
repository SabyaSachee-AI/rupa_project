import streamlit as st
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
from docx import Document
import io
import time
from openai import OpenAI

def process_files(files, pc_key, or_key):
    try:
        pc = Pinecone(api_key=pc_key)
        index = pc.Index("rupa-knowledge")
        client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
        
        all_text = ""
        for file in files:
            if file.name.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text: all_text += text + "\n"
            elif file.name.endswith(".docx"):
                doc = Document(io.BytesIO(file.read()))
                for para in doc.paragraphs:
                    all_text += para.text + "\n"
        
        if all_text:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            chunks = text_splitter.split_text(all_text)
            
            vectors = []
            batch_size = 50  # একবারে ৫০টি করে ভেক্টর পাঠানো হবে (Safe Limit)
            
            for i, chunk in enumerate(chunks):
                res = client.embeddings.create(input=chunk, model="text-embedding-3-small")
                embedding = res.data[0].embedding
                vectors.append({
                    "id": f"doc_{int(time.time())}_{i}",
                    "values": embedding,
                    "metadata": {"text": chunk}
                })
                
                # যদি ব্যাটচ সাইজ পূর্ণ হয়, তবে আপলোড করো এবং লিস্ট খালি করো
                if len(vectors) == batch_size:
                    index.upsert(vectors=vectors)
                    vectors = []
            
            # অবশিষ্ট ভেক্টরগুলো থাকলে সেগুলোও আপলোড করো
            if vectors:
                index.upsert(vectors=vectors)
            
            time.sleep(2)
            stats = index.describe_index_stats()
            count = stats['total_vector_count']
            st.success(f"সফলভাবে আপলোড হয়েছে! বর্তমানে মোট {count}টি তথ্য আছে।")
            return True
        return False
    except Exception as e:
        st.error(f"Pinecone Error: {e}")
        return False

def search_knowledge(query, pc_key, or_key):
    try:
        pc = Pinecone(api_key=pc_key)
        index = pc.Index("rupa-knowledge")
        client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
        
        res = client.embeddings.create(input=query, model="text-embedding-3-small")
        query_vector = res.data[0].embedding
        results = index.query(vector=query_vector, top_k=3, include_metadata=True)
        
        return "\n".join([m['metadata']['text'] for m in results['matches']])
    except:
        return ""