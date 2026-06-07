# Agentic RAG-Based Document Question Answering System

## Overview

The Agentic RAG-Based Document Question Answering System is an AI-powered application that enables users to upload documents and ask natural language questions about their content. The system leverages Retrieval-Augmented Generation (RAG) to retrieve relevant information from uploaded documents and generate accurate, context-aware responses using Large Language Models (LLMs).

## Features

- Upload and process PDF documents
- Intelligent document indexing and retrieval
- Natural language question answering
- Retrieval-Augmented Generation (RAG) pipeline
- Context-aware responses from LLMs
- Interactive web interface
- Fast semantic search using vector embeddings
- Scalable and modular architecture

## Tech Stack

### Frontend
- Streamlit

### Backend
- Python
- LangChain
- CrewAI / Agentic AI Framework

### AI & NLP
- OpenAI / LLM APIs
- Sentence Transformers
- Embedding Models

### Vector Database
- FAISS

### Document Processing
- PyPDF
- PDF Parsing Utilities

## System Architecture

1. User uploads document(s)
2. Documents are parsed and chunked
3. Text chunks are converted into vector embeddings
4. Embeddings are stored in FAISS Vector Database
5. User submits a query
6. Relevant document chunks are retrieved
7. Retrieved context is passed to the LLM
8. AI generates an accurate response based on document content

## Installation

### Clone Repository

```bash
git clone https://github.com/nischaysareen09/Agentic-RAG-Based-Document-Question-Answering-System.git
cd Agentic-RAG-Based-Document-Question-Answering-System
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / MacOS

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_api_key
```

Add any additional API keys required by the project.

## Run the Application

```bash
streamlit run app.py
```

## Usage

1. Launch the application.
2. Upload one or more PDF documents.
3. Wait for document indexing.
4. Enter your question in the chat interface.
5. Receive AI-generated answers based on document content.

## Project Structure

```text
├── app.py
├── data/
├── documents/
├── embeddings/
├── vectorstore/
├── utils/
├── requirements.txt
├── .env
└── README.md
```

## Future Enhancements

- Multi-document reasoning
- Chat history memory
- Source citation support
- Hybrid search (Keyword + Semantic)
- Support for DOCX, TXT, and Excel files
- Multi-agent orchestration
- Local LLM deployment

## Author

### Nischay Sareen

- B.Tech CSE (Data Science)
- AI/ML and Generative AI Enthusiast
- LinkedIn: https://www.linkedin.com/in/nischay-sareen/

## License

This project is intended for educational and research purposes.
