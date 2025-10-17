import os
import shutil
import requests
import traceback
import uuid
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# Removed Google embeddings to avoid quota errors
# from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from serpapi.google_search import GoogleSearch

# ✅ Load environment variables
load_dotenv()
app = Flask(__name__)

# Secret key: use explicit env var if present, otherwise generate a random fallback.
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.getenv("GOOGLE_API_KEY") or os.urandom(24)

# ✅ Configuration
app.config['UPLOAD_FOLDER'] = 'pdf_uploads'
VECTOR_BASE_FOLDER = "faiss_indexes"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(VECTOR_BASE_FOLDER, exist_ok=True)

# ✅ Extract text from PDF
def extract_text_from_pdf(file_path):
    text = ""
    pdf_reader = PdfReader(file_path)
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

# ✅ Split text into manageable chunks
def split_text(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return splitter.split_text(text)

# ✅ Create FAISS vector store with HuggingFace embeddings
def create_vector_store(chunks, folder_name):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(chunks, embedding=embeddings)
    save_path = os.path.join(VECTOR_BASE_FOLDER, folder_name)
    os.makedirs(save_path, exist_ok=True)
    vectorstore.save_local(save_path)

# ✅ QA chain (Gemini still used for answering, not embeddings)
from langchain_google_genai import ChatGoogleGenerativeAI

def load_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context.
    If the answer is not in the provided context, just say,
    "answer is not available in the context." Do not make up an answer.

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
    files = session.get("uploaded_files", [])
    return jsonify({"uploaded_files": files})

# ✅ Upload PDFs and create embeddings
@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        if "uploaded_files" not in session:
            session["uploaded_files"] = []

        files = request.files.getlist("files[]")
        if not files:
            return jsonify({"error": "No files provided"}), 400

        uploaded_filenames = []

        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                continue

            original_name = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(save_path)

            text = extract_text_from_pdf(save_path)
            chunks = split_text(text)
            vector_folder = os.path.splitext(unique_name)[0]

            try:
                create_vector_store(chunks, vector_folder)
            except Exception as ve:
                traceback.print_exc()
                try:
                    os.remove(save_path)
                except Exception:
                    pass
                return jsonify({"error": f"Failed to create vector store for {original_name}: {str(ve)}"}), 500

            try:
                os.remove(save_path)
            except Exception:
                pass

            session["uploaded_files"].append({
                "filename": unique_name,
                "vector_folder": vector_folder,
                "source": "upload"
            })
            uploaded_filenames.append(unique_name)

        session.modified = True
        return jsonify({"filenames": uploaded_filenames})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Server error while uploading PDFs", "details": str(e)}), 500

@app.route("/delete_pdf", methods=["POST"])
def delete_pdf():
    try:
        filename = request.form.get("filepath")
        if not filename:
            return jsonify({"success": False, "error": "No filename provided"}), 400

        file_info = next((f for f in session.get("uploaded_files", []) if f["filename"] == filename), None)
        if not file_info:
            return jsonify({"success": False, "error": "File not found in session"}), 404

        vector_folder = file_info["vector_folder"]
        folder_path = os.path.join(VECTOR_BASE_FOLDER, vector_folder)

        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

        session["uploaded_files"] = [f for f in session["uploaded_files"] if f["filename"] != filename]
        session.modified = True

        return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# ✅ Use HuggingFace embeddings here too
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(force=True)
        question = data.get("question")
        if not question:
            return jsonify({"answer": "❌ No question provided."}), 400

        if "uploaded_files" not in session or not session["uploaded_files"]:
            return jsonify({"answer": "❌ No PDFs uploaded yet. Please upload a PDF first."})

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
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
            except Exception:
                traceback.print_exc()
                continue

        if not all_docs:
            return jsonify({"answer": "🤷 No relevant context found in the uploaded documents."})

        chain = load_chain()
        answer = chain({"input_documents": all_docs, "question": question}, return_only_outputs=True)
        return jsonify({"answer": answer["output_text"]})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"answer": "❌ Server error while processing the question.", "details": str(e)}), 500

@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    return jsonify({"success": True})

@app.route("/search_scholar", methods=["POST"])
def search_scholar():
    try:
        data = request.get_json(force=True)
        query = data.get("query")
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
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/add_scholar_paper", methods=["POST"])
def add_scholar_paper():
    try:
        paper = request.get_json(force=True)
        title = paper.get("title")
        link = paper.get("link")

        if not link or not link.lower().endswith(".pdf"):
            return jsonify({"success": False, "error": "The link is not a direct PDF link."}), 400

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

        try:
            os.remove(filepath)
        except Exception:
            pass

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

        return jsonify({"success": True, "filename": filename, "title": title})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
