# Research Mate 🤖📚

**Research Mate** is an AI-powered research assistant that helps you interact with your research papers. Upload PDFs or search for papers directly from Google Scholar, then ask questions about your documents using AI-powered conversation.

---

## 🌟 Features
- 📄 **PDF Upload & Processing**: Upload and extract text from multiple PDFs
- 🔍 **Google Scholar Integration**: Search for research papers and add them directly
- 🤖 **AI-Powered Q&A**: Ask questions about your uploaded documents using Google's Gemini AI
- 🗂️ **Document Management**: View and delete uploaded documents
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 💬 **Real-time Chat Interface**: Interactive conversation with typing simulation
- 🔐 **Secure Processing**: Your documents are processed locally and not stored on external servers

---

## 🚀 Purpose
Research Mate is designed to help students, researchers, and academics:
- Quickly analyze research papers without reading them completely
- Find relevant information across multiple documents
- Discover new research papers through integrated Scholar search
- Get instant answers to specific questions about their research materials

---

## 🛠️ Technologies Used

### Backend
- **Python Flask** – Web framework  
- **LangChain** – AI application framework  
- **Google Gemini AI** – Language model for Q&A  
- **FAISS** – Vector similarity search  
- **PyPDF2** – PDF text extraction  
- **SerpAPI** – Google Scholar search integration  

### Frontend
- **HTML5/CSS3** – Structure and styling  
- **JavaScript** – Interactive functionality  
- **Bootstrap 5** – Responsive UI framework  

### APIs
- **Google Generative AI API** – For AI capabilities  
- **SerpAPI** – For Google Scholar search  

---

## 🔑 Getting API Keys

### Google API Key
1. Go to [Google AI Studio](https://studio.google.com/)  
2. Sign in with your Google account  
3. Create a new API key  
4. Copy the key to your `.env` file  

### SerpAPI Key
1. Go to [SerpAPI](https://serpapi.com/)  
2. Create a free account  
3. Find your API key in the dashboard  
4. Copy the key to your `.env` file  

---

## 📋 Prerequisites
Before running this project, make sure you have:
- Python 3.8 or higher  
- pip (Python package manager)  
- Google API key (for Gemini AI)  
- SerpAPI key (for Google Scholar search)

---

## 🏃‍♂️ How to Run Locally
1. **Clone the Repository**
   ```bash
   git clone https://github.com/KapilSehrawat2005/Research-Mate.git
   cd Research-Mate
2. **Install Dependencies**
   ```bash
    pip install -r requirements.txt

3. **Set Up Environment Variables**
   ```bash
   GOOGLE_API_KEY=your_google_api_key_here
    SERPAPI_KEY=your_serpapi_key_here
    FLASK_SECRET_KEY=your_random_secret_key_here

4. **Run the Application**
   ```bash
   python app.py
5. **Access the Application**
   Open http://localhost:5000
   in your browser.


## 📖 How to Use

### Uploading PDF Documents
1. Click on **"Choose File"** and select PDF documents  
2. Click **"Upload & Process PDFs"** button  
3. Wait for processing to complete  
4. View your documents in the **"Your Documents"** section  

### Searching Google Scholar
1. Enter your search query in the Scholar search bar  
2. Click **"Search"** to find relevant papers  
3. Review the results and click **"Add to Documents"** on relevant papers  
4. The system will automatically download and process the PDF  

### Asking Questions
1. Type your question in the chat input at the bottom  
2. Press **Enter** or click **"Ask"**  
3. The AI will search through all your documents and provide answers  
4. Continue the conversation with follow-up questions  

### Managing Documents
- View all uploaded documents in the **"Your Documents"** section  
- Delete any document by clicking the ❌ icon  
- Clear chat history with the **"Clear"** button  

---

## 📝 License
This project is licensed under the MIT License – see the LICENSE file for details.

---

## 👨‍💻 Developers
[Kapil Sehrawat](https://github.com/KapilSehrawat2005)
