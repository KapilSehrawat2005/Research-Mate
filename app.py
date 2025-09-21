import os
import shutil
import requests
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from serpapi.google_search import GoogleSearch
import uuid

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("GOOGLE_API_KEY", "SERPAPI_KEY")

# Configuration
app.config['UPLOAD_FOLDER'] = 'pdf_uploads'
VECTOR_BASE_FOLDER = "faiss_indexes"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(VECTOR_BASE_FOLDER, exist_ok=True)

def extract_text_from_pdf(file_path):
    text = ""
    pdf_reader = PdfReader(file_path)
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def split_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return splitter.split_text(text)

def create_vector_store(chunks, folder_name):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_texts(chunks, embedding=embeddings)
    vectorstore.save_local(os.path.join(VECTOR_BASE_FOLDER, folder_name))

def load_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in
    the provided context, just say, "answer is not available in the context." Do not make up an answer.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/developer")
def developer():
    return render_template("developers.html")

@app.route("/workflow")
def workflow():
    return render_template("workflow.html")

@app.route("/session_data")
def session_data():
    """Endpoint to get current session data for frontend initialization"""
    files = session.get("uploaded_files", [])
    return jsonify({
        "uploaded_files": files
    })

@app.route("/upload", methods=["POST"])
def upload_files():
    if "uploaded_files" not in session:
        session["uploaded_files"] = []

    files = request.files.getlist("files[]")
    uploaded = []

    for file in files:
        if file.filename.endswith(".pdf"):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            text = extract_text_from_pdf(filepath)
            chunks = split_text(text)
            vector_folder = os.path.splitext(filename)[0]
            create_vector_store(chunks, vector_folder)

            session["uploaded_files"].append({
                "filename": filename,
                "vector_folder": vector_folder,
                "source": "upload"
            })
            uploaded.append(filepath)

            os.remove(filepath)

    session.modified = True
    return jsonify({"filenames": uploaded})

@app.route("/delete_pdf", methods=["POST"])
def delete_pdf():
    filename = request.form.get("filepath")
    if not filename:
        return jsonify({"success": False, "error": "No filename provided"}), 400

    # Find the file in session
    file_info = next((f for f in session.get("uploaded_files", []) if f["filename"] == filename), None)
    
    if not file_info:
        return jsonify({"success": False, "error": "File not found in session"}), 404

    # Delete vector store
    vector_folder = file_info["vector_folder"]
    folder_path = os.path.join(VECTOR_BASE_FOLDER, vector_folder)
    
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)

    # Remove from session
    if "uploaded_files" in session:
        session["uploaded_files"] = [f for f in session["uploaded_files"] if f["filename"] != filename]
        session.modified = True

    return jsonify({"success": True})

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question")
    if "uploaded_files" not in session or not session["uploaded_files"]:
        return jsonify({"answer": "❌ No PDFs uploaded yet. Please upload a PDF first."})

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    all_docs = []

    for file_info in session["uploaded_files"]:
        try:
            vectorstore = FAISS.load_local(
                os.path.join(VECTOR_BASE_FOLDER, file_info["vector_folder"]),
                embeddings,
                allow_dangerous_deserialization=True
            )
            docs = vectorstore.similarity_search(question, k=2)
            all_docs.extend(docs)
        except Exception as e:
            print(f"Error loading vector store for {file_info['filename']}: {str(e)}")
            continue

    if not all_docs:
        return jsonify({"answer": "🤷 No relevant context found in the uploaded documents."})

    chain = load_chain()
    answer = chain({"input_documents": all_docs, "question": question}, return_only_outputs=True)
    return jsonify({"answer": answer["output_text"]})

@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    # Only clear chat history, not documents
    return jsonify({"success": True})

@app.route("/search_scholar", methods=["POST"])
def search_scholar():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "No query provided."}), 400

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": os.getenv("SERPAPI_KEY")
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    papers = []

    for result in results.get("organic_results", []):
        paper = {
            "title": result.get("title"),
            "link": result.get("link"),
            "snippet": result.get("snippet"),
            "publication_info": result.get("publication_info", {}).get("summary", "")
        }
        papers.append(paper)

    return jsonify({"papers": papers})

@app.route("/add_scholar_paper", methods=["POST"])
def add_scholar_paper():
    paper = request.json
    title = paper.get("title")
    link = paper.get("link")

    if not link or not link.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "The link is not a direct PDF link."}), 400

    try:
        response = requests.get(link, stream=True, timeout=15)
        if 'application/pdf' not in response.headers.get('content-type', ''):
            return jsonify({"success": False, "error": "The link does not lead to a PDF file."}), 400

        filename = f"scholar_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)

        text = extract_text_from_pdf(filepath)
        chunks = split_text(text)
        vector_folder = os.path.splitext(filename)[0]
        create_vector_store(chunks, vector_folder)

        os.remove(filepath)

        if "uploaded_files" not in session:
            session["uploaded_files"] = []

        session["uploaded_files"].append({
            "filename": filename,
            "vector_folder": vector_folder,
            "source": "scholar",
            "title": title,
            "link": link
        })
        session.modified = True

        return jsonify({
            "success": True,
            "filename": filename,
            "title": title
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)