# CIE-GPT : The Innovation Whisperer

A **GenAI** powered **Course Companion** for CIE's Essentials of Innovation and Entrepreneurship ( EIE ), helping students understand and interact with coursework through **RAG** ( Retrieval Augmented Generation ) and **LLM** technologies.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [RAGAs](#ragas)

### Features

- **Multimodal Ingestion** : Processes Text, PDFs, PPTs and Videos.
- **Smart Retrieval** : Uses vector databases and LLMs for smart responses.
- **24/7 Course Assistance** : Answers syllabus-grounded questions.

### Architecture

#### System Overview

![Detailed Architecture Diagram](frontend\public\Deployment_diagram.png)
![Architecture Diagram](frontend\public\AdyanshDiagram.jpeg)

#### Technology Stack

- **Backend** : Python, FastAPI
- **Vector Databases** : Qdrant, FAISS
- **LLM Integration** : MistralAI, DeepSeek and Phi-3-mini ( although only MistralAI was used for the Demo )
- **RAG Framework** : LlamaIndex
- **Session Management** : WebSocket, Redis
- **Frontend** : ReactJS, Typescript

### Installation

#### To run backend

<pre>
Run requirements.txt

<i>Without Kafka</i>
cd backend
uvicorn api.app0:app --reload --port 8500 

<i>With Kafka</i>
cd backend
uvicorn api.app1:app --reload --port 8500
</pre>

_Note: To run Kafka, you need to setup a Docker Image of the Kafka container in the code_

#### To run frontend

<pre>
cd frontend
npm install
npm run dev</pre>

#### To run Redis

<pre>
1. Start Ubuntu
2. sudo server redis-service start
3. redis-cli ping <i>this must return PONG, which indicates redis is working</i>
</pre>

### RAGAs

Our Course Companion includes a comprehensive **RAG Assessment and Grading System** (_RAGAs_) designed to evaluate the quality and accuracy of the RAG pipeline responses.

#### Overview

As part of our RAG evaluation pipeline, we developed a fully local version of RAGAs that operates without external LLM dependencies (OpenAI). The system takes a user query from the UI, retrieves the corresponding ground truth from a preloaded dataset (stored as JSON), and evaluates the LLM-generated response from the RAG pipeline.

#### Key Features

- 470+ Evaluation Questions
- Fully local operation
- Multiple Metrics
- Visual Analytics
- Structured Logging

#### Evaluation Metrics

RAGAs system computes the following metrics using TF-IDF and cosine similarity techniques :

1. Context Relevance
2. Context Precision
3. Context Recall
4. Answer Relevance
5. Answer Correctness

These metrics help quantify how well the retrieved contexts and the LLM response align with the original ground truth.

_Note: The code for the RAGAs implementation currently exists, however we are yet to perform the benchmarking_
