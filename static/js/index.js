document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const chatForm = document.getElementById('chat-form');
    const questionInput = document.getElementById('question');
    const chatArea = document.getElementById('chat-area');
    const pdfContainer = document.getElementById('pdf-container');
    const clearBtn = document.getElementById('clear-chat');
    const scholarForm = document.getElementById('scholar-search-form');
    const scholarInput = document.getElementById('scholar-query');
    const searchResults = document.getElementById('search-results');

    // Initialize session data
    initializeSessionData();

    // Upload form handler
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = "Processing...";
        
        document.getElementById("upload-progress").style.display = "block";
        document.getElementById("progress-bar-text").style.width = "100%";

        const formData = new FormData(uploadForm);
        try {
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.filenames) {
                await initializeSessionData(); // Refresh the document list
            }
        } catch (error) {
            console.error("Upload error:", error);
            pdfContainer.innerHTML = `<div class="alert alert-danger">❌ Failed to upload or process PDFs: ${error.message}</div>`;
        } finally {
            document.getElementById("upload-progress").style.display = "none";
            submitBtn.disabled = false;
            submitBtn.textContent = "Upload & Process PDFs";
        }
    });

    // Render PDF list function
    function renderPDFList(files) {
        pdfContainer.innerHTML = '';

        if (files.length === 0) {
            pdfContainer.innerHTML = '<div>No documents uploaded yet.</div>';
            return;
        }

        files.forEach(file => {
            const div = document.createElement('div');
            div.className = 'pdf-item';
            if (file.source === "scholar") div.classList.add('scholarly');

            if (file.source === "scholar") {
                div.innerHTML = `
                    <div class="flex-grow-1">
                        <strong>${file.title || 'Scholar Paper'}</strong>
                        ${file.link ? `<br><small><a href="${file.link}" target="_blank">View Source</a></small>` : ''}
                    </div>
                    <span class="delete-pdf" title="Delete PDF">❌</span>
                `;
            } else {
                div.innerHTML = `
                    <div class="flex-grow-1">${file.filename}</div>
                    <span class="delete-pdf" title="Delete PDF">❌</span>
                `;
            }

            // Add delete handler
            div.querySelector('.delete-pdf').addEventListener('click', async () => {
                if (confirm("Are you sure you want to delete this document?")) {
                    const res = await fetch('/delete_pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `filepath=${encodeURIComponent(file.filename)}`
                    });
                    
                    const data = await res.json();
                    if (data.success) {
                        await initializeSessionData(); // Refresh the list
                    } else {
                        alert("Failed to delete document: " + (data.error || 'Unknown error'));
                    }
                }
            });

            pdfContainer.appendChild(div);
        });
    }

    // Chat form handler
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;

        // Add user question to chat
        chatArea.innerHTML += `<div class='chat-box user'>🧑‍🎓 You: ${question}</div>`;
        const tempId = `bot-temp-${Date.now()}`;
        chatArea.innerHTML += `<div class='chat-box bot' id='${tempId}'>🤖 Research Mate: Thinking...</div>`;
        questionInput.value = '';
        questionInput.disabled = true;

        try {
            const res = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            
            const data = await res.json();
            if (data.answer) {
                await simulateTyping(document.getElementById(tempId), data.answer);
            } else {
                document.getElementById(tempId).innerHTML = `🤖 Research Mate: ❌ Error processing the question.`;
            }
        } catch (error) {
            console.error("Ask error:", error);
            document.getElementById(tempId).innerHTML = `🤖 Research Mate: ❌ Network error occurred.`;
        } finally {
            questionInput.disabled = false;
            questionInput.focus();
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    });

    // Typing simulation
    async function simulateTyping(element, text) {
        element.innerHTML = "🤖 Research Mate: ";
        for (let i = 0; i < text.length; i++) {
            element.innerHTML += text.charAt(i);
            await new Promise(r => setTimeout(r, 20));
        }
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    clearBtn.addEventListener('click', () => {
    if (confirm("Are you sure you want to clear the chat history?")) {
        chatArea.innerHTML = '';
    }
});

    // Scholar search handler
    scholarForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = scholarInput.value.trim();
        if (!query) return;

        searchResults.style.display = "block";
        searchResults.innerHTML = "<div class='text-center my-3'>🔎 Searching Google Scholar...</div>";

        try {
            const res = await fetch('/search_scholar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            
            const data = await res.json();
            searchResults.innerHTML = "";

            if (!data.papers || data.papers.length === 0) {
                searchResults.innerHTML = "<div class='alert alert-warning'>❌ No results found for your query.</div>";
                return;
            }

            const resultsHeader = document.createElement('h5');
            resultsHeader.className = "mb-3";
            resultsHeader.textContent = "📚 Search Results:";
            searchResults.appendChild(resultsHeader);

            data.papers.forEach(paper => {
                const div = document.createElement('div');
                div.className = "border p-3 mb-3 rounded";
                
                div.innerHTML = `
                    <h5>${paper.title}</h5>
                    ${paper.publication_info ? `<p class="text-info small mb-1">${paper.publication_info}</p>` : ''}
                    ${paper.snippet ? `<p class="mb-2">${paper.snippet}</p>` : ''}
                    <div class="d-flex gap-2">
                        <a href="${paper.link}" target="_blank" class="btn btn-sm btn-outline-primary">View Paper</a>
                        <button class="btn btn-sm btn-success add-paper-btn">Add to Documents</button>
                    </div>
                `;

                const addBtn = div.querySelector('.add-paper-btn');
                addBtn.addEventListener('click', async () => {
                    addBtn.disabled = true;
                    addBtn.textContent = "Adding...";
                    
                    try {
                        const addRes = await fetch('/add_scholar_paper', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(paper)
                        });
                        
                        const addData = await addRes.json();
                        if (addData.success) {
                            addBtn.textContent = "✓ Added";
                            await initializeSessionData();
                        } else {
                            addBtn.textContent = "Failed";
                            alert(addData.error || "Failed to add paper");
                        }
                    } catch (error) {
                        console.error("Add paper error:", error);
                        addBtn.textContent = "Error";
                    } finally {
                        setTimeout(() => {
                            addBtn.disabled = false;
                            addBtn.textContent = "Add to Documents";
                        }, 2000);
                    }
                });

                searchResults.appendChild(div);
            });
        } catch (error) {
            console.error("Scholar search error:", error);
            searchResults.innerHTML = `<div class="alert alert-danger">❌ Failed to fetch search results: ${error.message}</div>`;
        }
    });

    // Initialize session data
    async function initializeSessionData() {
        try {
            const res = await fetch('/session_data');
            const data = await res.json();
            
            if (data.uploaded_files) {
                renderPDFList(data.uploaded_files);
            } else {
                pdfContainer.innerHTML = '<div class="text-info">No documents uploaded yet.</div>';
            }
        } catch (error) {
            console.error("Session data error:", error);
        }
    }

});
    
    
    const chatArea = document.getElementById('chat-area');
    function scrollToBottom() {
      chatArea.scrollTop = chatArea.scrollHeight;
    }
    function addMessage(isUser, text) {
      const messageDiv = document.createElement('div');
      messageDiv.className = `chat-box ${isUser ? 'user' : 'bot'}`;
      messageDiv.innerHTML = `${isUser ? '🧑‍🎓 You' : '🤖 Research Mate'}: ${text}`;
      chatArea.appendChild(messageDiv);
      scrollToBottom();
    }

//     document.getElementById('delete-all-docs').addEventListener('click', async () => {
//     if (confirm("Are you sure you want to delete ALL documents? This cannot be undone.")) {
//         try {
//             const res = await fetch('/clear_chat', { method: 'POST' });
//             const data = await res.json();
//             if (data.success) {
//                 await initializeSessionData(); // Refresh document list
//                 chatArea.innerHTML = ''; // Also clear chat
//             }
//         } catch (error) {
//             console.error("Delete all error:", error);
//         }
//     }
// });