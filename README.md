# CIE_RAG

## backend
change pwd to backend - preferably work in a virtual env.
Run - requirements.txt
```
fastapi
uvicorn
python-dotenv
requests
gdown
PyMuPDF
python-docx
openpyxl
python-pptx
Pillow
gradio
moviepy
transformers
torch
sentence-transformers
qdrant-client
faiss-cpu
llama-index
numpy
pandas

```
Then run the following code 

```uvicorn api.app:app --reload --port 8000```

## frontend 

First change pwd to frontend, then run the following commands (make sure u have Node install)

``` npm install ```
``` npm run dev ```