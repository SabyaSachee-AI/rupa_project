# 🤖 Rupa AI - Intelligent Bilingual Assistant

**Rupa AI** is a state-of-the-art bilingual (Bangla & English) AI assistant designed to provide meaningful conversations, information retrieval, and personalized interactions. Built with Python and Streamlit, it leverages advanced LLMs and Vector Databases to provide a seamless user experience.

---

## 🚀 Live Demo


---

## ✨ Features
- **Bilingual Support:** Communicates fluently in both Bangla and English.
- **Contextual Memory:** Remembers past interactions for more personalized responses using Pinecone Vector DB.
- **Fast Inference:** Uses Groq and OpenRouter for lightning-fast AI responses.
- **Modern UI:** A clean, responsive interface built with Streamlit.
- **Cloud Native:** Fully containerized with Docker for easy deployment.

---

## 🛠️ Tech Stack
- **Frontend:** [Streamlit](https://streamlit.io/)
- **AI Models:** Groq (Llama 3), OpenRouter
- **Vector Database:** [Pinecone](https://www.pinecone.io/) (for long-term memory)
- **Framework:** LangChain
- **Deployment:** Hugging Face Spaces & Docker

---

## ⚙️ Installation & Local Setup

To run this project locally, follow these steps:


```bash
1. Clone the repository

git clone [https://github.com/sabyasacheedas/rupa-ai.git](https://github.com/sabyasacheedas/rupa-ai.git)
cd rupa-ai


2. Create a virtual environment

      ython -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies
     pip install -r requirements.txt

4. Setup Environment Variables
    Create a .env file in the root directory and add your API keys:

    Code snippet

        OPENROUTER_API_KEY=your_openrouter_key
        GROQ_API_KEY=your_groq_key
        PINECONE_API_KEY=your_pinecone_key

5. Run the application

        streamlit run main.py 

