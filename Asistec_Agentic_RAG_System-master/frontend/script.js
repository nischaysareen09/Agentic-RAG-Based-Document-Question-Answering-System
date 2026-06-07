document.addEventListener('DOMContentLoaded', () => {
    // --- CONFIGURATION ---
    const API_BASE_URL = 'http://localhost:8000';

    // --- STATE ---
    let currentUserId = null;
    let currentThreadId = null;
    let threads = [];
    let isMobileView = window.innerWidth <= 768;
    let activePopover = null;
    let currentView = 'chat'; // 'chat' or 'memories'

    // --- DOM ELEMENTS ---
    const userIdModal = document.getElementById('user-id-modal');
    const userIdForm = document.getElementById('user-id-form');
    const userIdInput = document.getElementById('user-id-input');
    const userIdError = document.getElementById('user-id-error');
    const userIdSubmitButton = userIdForm.querySelector('button[type="submit"]');
    
    const appContainer = document.querySelector('.app-container');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleButtonDesktop = document.getElementById('sidebar-toggle-button-desktop');
    const sidebarToggleButtonMobile = document.getElementById('sidebar-toggle-button-mobile');

    const newChatButton = document.getElementById('new-chat-button');
    const threadSearchInput = document.getElementById('thread-search-input');
    const threadList = document.getElementById('thread-list');
    
    const currentChatTitle = document.getElementById('current-chat-title');
    const welcomeScreen = document.getElementById('welcome-screen');
    const welcomeGreeting = document.getElementById('welcome-greeting');
    const messagesContainer = document.getElementById('messages-container');
    
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    const currentUserDisplay = document.getElementById('current-user-id-display');
    const userAvatar = document.getElementById('user-avatar');

    // START: Memories DOM Elements
    const memoriesSectionButton = document.getElementById('memories-section-button');
    const memoriesView = document.getElementById('memories-view');
    const deleteAllMemoriesButton = document.getElementById('delete-all-memories-button');
    const memoriesListContainer = document.getElementById('memories-list-container');
    const memoriesLoading = document.getElementById('memories-loading');
    const memoriesEmpty = document.getElementById('memories-empty');
    // END: Memories DOM Elements

    // --- API HELPER ---
    async function apiCall(endpoint, method = 'GET', body = null, rawResponse = false) {
        const url = `${API_BASE_URL}${endpoint}`;
        const options = { method, headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' } };
        if (body) options.body = JSON.stringify(body);

        try {
            const response = await fetch(url, options);
            if (rawResponse && response.ok) return response;
            const responseData = await response.json().catch(() => null);

            if (!response.ok) {
                const errorMsg = responseData?.detail?.[0]?.msg || responseData?.detail || `Error: ${response.status} ${response.statusText}`;
                console.error(`API Error (${method} ${url}):`, errorMsg, responseData);
                throw new Error(errorMsg);
            }
            return responseData;
        } catch (error) {
            console.error(`Network or parsing error (${method} ${url}):`, error);
            if (userIdModal.classList.contains('active')) {
                userIdError.textContent = `Network or API Error: ${error.message}`;
            } else if (currentView === 'chat') {
                addMessageToChat('system', `API Error: ${error.message}. Please try again.`);
            } else if (currentView === 'memories') {
                addSystemMessageToMemoriesView(`API Error: ${error.message}. Please try again.`, 'error');
            }
            throw error;
        }
    }

    // --- UI HELPERS ---
    function showButtonLoader(button) { button.classList.add('loading'); button.disabled = true; }
    function hideButtonLoader(button) { button.classList.remove('loading'); button.disabled = false; }

    // --- USER AUTHENTICATION ---
    userIdForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userIdVal = userIdInput.value.trim();
        if (!userIdVal) { userIdError.textContent = 'User ID cannot be empty.'; return; }
        userIdError.textContent = '';
        showButtonLoader(userIdSubmitButton);
        try { await checkAndLoginUser(userIdVal); } 
        catch (error) { userIdError.textContent = `Login failed: ${error.message}`; } 
        finally { hideButtonLoader(userIdSubmitButton); }
    });

    async function checkAndLoginUser(userIdVal) {
        try {
            const user = await apiCall(`/api/users/${userIdVal}`);
            loginUser(user.user_id);
        } catch (error) {
            console.log(`User ${userIdVal} not found, attempting to create.`);
            try {
                const newUser = await apiCall('/api/users', 'POST', { user_id: userIdVal });
                loginUser(newUser.user_id);
            } catch (createError) {
                console.error('Failed to create user:', createError);
                userIdError.textContent = `Failed to create or find user: ${createError.message}`;
                throw createError;
            }
        }
    }

    function loginUser(userIdVal) {
        currentUserId = userIdVal;
        userIdModal.classList.remove('active');
        appContainer.style.opacity = '1';
        currentUserDisplay.textContent = currentUserId;
        userAvatar.textContent = currentUserId.substring(0, 2).toUpperCase();
        
        loadUserThreads();
        showWelcomeScreen(); // Default to welcome screen on login
        
        adjustTextareaHeight(messageInput);
    }

    // --- SIDEBAR ---
    function toggleSidebar() {
        if (isMobileView) {
            sidebar.classList.toggle('open');
        } else {
            sidebar.classList.toggle('closed');
        }
    }
    sidebarToggleButtonDesktop.addEventListener('click', toggleSidebar);
    sidebarToggleButtonMobile.addEventListener('click', toggleSidebar);

    document.addEventListener('click', (event) => {
        if (isMobileView && sidebar.classList.contains('open')) {
            if (!sidebar.contains(event.target) && !sidebarToggleButtonDesktop.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        }
        if (activePopover && !activePopover.contains(event.target) && !event.target.closest('.thread-actions-button')) {
            closeActivePopover();
        }
    });

    // --- THREAD MANAGEMENT ---
    async function loadUserThreads(searchTerm = '') {
        if (!currentUserId) return;
        try {
            let fetchedThreads = await apiCall(`/api/threads?user_id=${currentUserId}`);
            if (searchTerm) {
                fetchedThreads = fetchedThreads.filter(thread => 
                    (thread.title || "New Chat").toLowerCase().includes(searchTerm.toLowerCase())
                );
            }
            threads = fetchedThreads; 
            renderThreads();
        } catch (error) {
            console.error('Failed to load threads:', error);
            // Optionally show error in thread list area
        }
    }

    threadSearchInput.addEventListener('input', (e) => { loadUserThreads(e.target.value.trim()); });

    function renderThreads() {
        threadList.innerHTML = '';
        if (threads.length === 0 && threadSearchInput.value) { 
            threadList.innerHTML = `<li class="no-threads-message">No chats found for "${threadSearchInput.value}".</li>`;
            return;
        }
        if (threads.length === 0 && !threadSearchInput.value) {
            threadList.innerHTML = `<li class="no-threads-message">No recent chats. Start a new one!</li>`;
            return;
        }

        const sortedThreads = [...threads].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        
        sortedThreads.forEach(thread => {
            const li = document.createElement('li');
            li.dataset.threadId = thread.id;
            li.classList.toggle('active-thread', thread.id === currentThreadId && currentView === 'chat');

            const titleSpan = document.createElement('span');
            titleSpan.className = 'thread-title';
            titleSpan.textContent = thread.title || 'Untitled Chat';
            titleSpan.title = thread.title || 'Untitled Chat';
            li.appendChild(titleSpan);
            
            const actionsButton = document.createElement('button');
            actionsButton.className = 'thread-actions-button';
            actionsButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>`;
            actionsButton.title = 'More options';
            
            const popover = document.createElement('div');
            popover.className = 'thread-actions-popover';
            popover.innerHTML = `
                <button class="rename-action" data-thread-id="${thread.id}" data-current-title="${thread.title || 'Untitled Chat'}">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                    Rename
                </button>
                <button class="delete-action" data-thread-id="${thread.id}">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    Delete
                </button>
            `;
            
            actionsButton.addEventListener('click', (e) => { e.stopPropagation(); togglePopover(popover); });
            popover.querySelector('.rename-action').addEventListener('click', (e) => { e.stopPropagation(); promptRenameThread(thread.id, thread.title || 'Untitled Chat'); closeActivePopover(); });
            popover.querySelector('.delete-action').addEventListener('click', (e) => { e.stopPropagation(); confirmDeleteThread(thread.id); closeActivePopover(); });

            li.appendChild(actionsButton);
            li.appendChild(popover);
            
            li.addEventListener('click', () => {
                loadThreadChat(thread.id, thread.title);
                if (isMobileView && sidebar.classList.contains('open')) sidebar.classList.remove('open');
                closeActivePopover();
            });
            threadList.appendChild(li);
        });
    }

    function togglePopover(popoverElement) {
        if (activePopover && activePopover !== popoverElement) activePopover.classList.remove('active');
        popoverElement.classList.toggle('active');
        activePopover = popoverElement.classList.contains('active') ? popoverElement : null;
    }
    function closeActivePopover() { if (activePopover) { activePopover.classList.remove('active'); activePopover = null; } }

    newChatButton.addEventListener('click', async () => {
        if (!currentUserId) return;
        try {
            currentThreadId = null; 
            clearMessages();
            setActiveScreen(welcomeScreen, 'chat'); // Ensure correct view and active sidebar item
            // currentChatTitle.textContent = "New Chat"; // Set by showWelcomeScreen or setActiveScreen logic
            messageInput.focus();
            // renderThreads(); // Already called by setActiveScreen logic via loadThreadChat if needed
            closeActivePopover();
            if (isMobileView && sidebar.classList.contains('open')) sidebar.classList.remove('open');
        } catch (error) { console.error('Failed to prepare new chat:', error); }
    });

    async function promptRenameThread(threadId, currentTitle) {
        const newTitle = prompt('Enter new title for the thread:', currentTitle || 'Untitled Chat');
        if (newTitle && newTitle.trim() !== '' && newTitle.trim() !== currentTitle) {
            try {
                await apiCall(`/api/threads/${threadId}`, 'PATCH', { title: newTitle.trim() });
                if (threadId === currentThreadId) currentChatTitle.textContent = newTitle.trim();
                loadUserThreads(threadSearchInput.value.trim()); 
            } catch (error) { console.error('Failed to rename thread:', error); }
        }
    }
    async function confirmDeleteThread(threadId) {
         if (confirm('Are you sure you want to delete this thread? This action cannot be undone.')) {
            try {
                await apiCall(`/api/threads/${threadId}`, 'DELETE', null, true);
                if (threadId === currentThreadId) {
                    currentThreadId = null;
                    clearMessages();
                    showWelcomeScreen(); // This will also call setActiveScreen
                }
                loadUserThreads(threadSearchInput.value.trim());
            } catch (error) { console.error('Failed to delete thread:', error); }
        }
    }

    // --- CHAT FUNCTIONALITY ---
    async function loadThreadChat(threadId, threadTitle) {
        if (currentThreadId === threadId && messagesContainer.classList.contains('active')) return; 

        currentThreadId = threadId;
        setActiveScreen(messagesContainer, 'chat'); // This handles active item and view
        currentChatTitle.textContent = threadTitle || "Chat";
        clearMessages();

        try {
            addTypingIndicator();
            const messages = await apiCall(`/api/threads/${threadId}/messages`);
            removeTypingIndicator();
            messages.forEach(msg => addMessageToChat(msg.role, msg.content));
            scrollToBottom();
            messageInput.focus();
        } catch (error) {
            removeTypingIndicator();
            console.error(`Failed to load messages for thread ${threadId}:`, error);
        }
    }

    let typingIndicatorElement = null;
    function addTypingIndicator() {
        if (typingIndicatorElement || currentView !== 'chat') return;
        typingIndicatorElement = document.createElement('div');
        typingIndicatorElement.className = 'message typing-indicator';
        typingIndicatorElement.innerHTML = '<span></span><span></span><span></span>';
        messagesContainer.appendChild(typingIndicatorElement);
        scrollToBottom();
    }
    function removeTypingIndicator() {
        if (typingIndicatorElement) { typingIndicatorElement.remove(); typingIndicatorElement = null; }
    }

    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const messageText = messageInput.value.trim();
        if (!messageText || !currentUserId) return;

        showButtonLoader(sendButton);
        addMessageToChat('user', messageText);
        messageInput.value = '';
        adjustTextareaHeight(messageInput);
        scrollToBottom();
        addTypingIndicator();

        let threadToUse = currentThreadId;

        try {
            if (!threadToUse) {
                const newThread = await apiCall('/api/threads', 'POST', { user_id: currentUserId });
                threads.push(newThread);
                threadToUse = newThread.id;
                currentThreadId = newThread.id;
                setActiveScreen(messagesContainer, 'chat'); // Switch from welcome if it was showing
                currentChatTitle.textContent = newThread.title || "New Chat";
                loadUserThreads(threadSearchInput.value.trim()); // To show new thread in list
            }

            const response = await apiCall(`/api/threads/${threadToUse}/messages`, 'POST', {
                content: messageText,
                user_id: currentUserId
            });
            removeTypingIndicator();
            addMessageToChat('assistant', response.assistant_message);
            
            const threadIndex = threads.findIndex(t => t.id === threadToUse);
            if (threadIndex > -1) {
                threads[threadIndex].updated_at = new Date().toISOString();
                renderThreads(); 
            }
        } catch (error) {
            removeTypingIndicator();
        } finally {
            hideButtonLoader(sendButton);
            scrollToBottom();
            messageInput.focus();
        }
    });

    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        if (role === 'user') messageDiv.classList.add('user-message');
        else if (role === 'assistant') messageDiv.classList.add('assistant-message');
        else messageDiv.classList.add('system-message');
        
        const contentP = document.createElement('p');
        content = content.replace(/\[(.*?)\]\((https?:\/\/[^\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        content = content.replace(/`(.*?)`/g, '<code>$1</code>');
        content = content.replace(/\n/g, '<br>');
        contentP.innerHTML = content;

        messageDiv.appendChild(contentP);
        messagesContainer.appendChild(messageDiv);
    }

    function clearMessages() { messagesContainer.innerHTML = ''; removeTypingIndicator(); }
    function scrollToBottom() { 
        const view = currentView === 'chat' ? document.getElementById('chat-view') : memoriesView;
        if (view) view.scrollTop = view.scrollHeight;
    }
    
    function setActiveScreen(activeElement, viewType) {
        currentView = viewType; // Set currentView first

        welcomeScreen.classList.remove('active');
        messagesContainer.classList.remove('active');
        memoriesView.classList.remove('active');
        
        document.querySelectorAll('#thread-list li').forEach(li => li.classList.remove('active-thread'));
        document.querySelectorAll('.sidebar-nav-item').forEach(item => item.classList.remove('active'));

        if (activeElement) activeElement.classList.add('active');

        if (currentView === 'chat') {
            if (currentThreadId) {
                const activeThreadLi = threadList.querySelector(`li[data-thread-id="${currentThreadId}"]`);
                if (activeThreadLi) activeThreadLi.classList.add('active-thread');
            }
             // currentChatTitle is set by loadThreadChat or showWelcomeScreen
        } else if (currentView === 'memories') {
            memoriesSectionButton.classList.add('active');
            currentChatTitle.textContent = "My Memories";
        }
        renderThreads(); // Re-render threads to update active state correctly
    }

    function showWelcomeScreen() {
        currentThreadId = null; // No active thread on welcome screen
        currentChatTitle.textContent = ""; 
        welcomeGreeting.textContent = `Good Morning, ${currentUserId || 'Guest'}!`;
        setActiveScreen(welcomeScreen, 'chat');
    }

    function adjustTextareaHeight(textarea) {
        textarea.style.height = 'auto'; 
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    }
    messageInput.addEventListener('input', () => adjustTextareaHeight(messageInput));
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if(!sendButton.disabled) messageForm.requestSubmit(); 
        }
    });

    // --- MEMORIES FUNCTIONALITY ---
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        try {
            return new Date(dateString).toLocaleDateString(undefined, options);
        } catch (e) {
            return dateString;
        }
    }

    function addSystemMessageToMemoriesView(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `memories-view-feedback ${type}`; // CSS handles success/error
        messageDiv.textContent = message;
        
        // Insert before loading/empty feedback, or at the top of the list
        const firstChild = memoriesListContainer.firstChild;
        if (firstChild) {
            memoriesListContainer.insertBefore(messageDiv, firstChild);
        } else {
            memoriesListContainer.appendChild(messageDiv);
        }
        
        setTimeout(() => {
            if (messageDiv.parentNode) messageDiv.remove();
        }, 5000);
    }

    async function loadUserMemories() {
        if (!currentUserId) return;

        memoriesListContainer.innerHTML = ''; // Clear previous content, including feedback messages
        memoriesLoading.style.display = 'block';
        memoriesEmpty.style.display = 'none';
        deleteAllMemoriesButton.disabled = true; // Disable while loading

        try {
            const data = await apiCall(`/api/memories?user_id=${currentUserId}`);
            renderMemories(data.memories || []);
        } catch (error) {
            console.error('Failed to load memories:', error);
            // Error message is handled by apiCall and addSystemMessageToMemoriesView
            memoriesEmpty.style.display = 'block'; // Show empty if load failed
        } finally {
            memoriesLoading.style.display = 'none';
        }
    }

    function renderMemories(memories) {
        // Clear only if we are about to render actual items, keep feedback messages if any
        // memoriesListContainer.innerHTML = ''; // Clearing is now done in loadUserMemories

        if (memories.length === 0) {
            memoriesEmpty.style.display = 'block';
            deleteAllMemoriesButton.disabled = true;
        } else {
            memoriesEmpty.style.display = 'none';
            deleteAllMemoriesButton.disabled = false;
        }

        memories.forEach(memory => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'memory-item';
            itemDiv.innerHTML = `
                <div class="memory-content">
                    <p>${memory.memory.replace(/\n/g, '<br>')}</p>
                    <div class="memory-meta">Created: ${formatDate(memory.created_at)}</div>
                </div>
                <button class="memory-delete-button" data-memory-id="${memory.id}" title="Delete Memory">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zm2.46-7.12l1.41-1.41L12 12.17l2.12-2.12 1.41 1.41L13.41 13.5l2.12 2.12-1.41 1.41L12 14.93l-2.12 2.12-1.41-1.41L10.59 13.5l-2.13-2.12zM15.5 4l-1-1h-5l-1 1H5v2h14V4z"/>
                    </svg>
                </button>
            `;
            memoriesListContainer.appendChild(itemDiv);
        });
        scrollToBottom(); // Scroll if new memories made view longer
    }

    function showMemoriesView() {
        currentThreadId = null;
        setActiveScreen(memoriesView, 'memories');
        // currentChatTitle.textContent = 'My Memories'; // Handled by setActiveScreen
        loadUserMemories();
        if (isMobileView && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    }

    memoriesSectionButton.addEventListener('click', showMemoriesView);

    memoriesListContainer.addEventListener('click', async (event) => {
        const deleteButton = event.target.closest('.memory-delete-button');
        if (deleteButton && !deleteButton.disabled) {
            const memoryId = deleteButton.dataset.memoryId;
            if (memoryId && confirm('Are you sure you want to delete this memory?')) {
                deleteButton.disabled = true; // Disable button during operation
                try {
                    await apiCall(`/api/memories/${memoryId}`, 'DELETE');
                    addSystemMessageToMemoriesView("Memory deleted successfully.", "success");
                    // Find and remove the item directly from DOM for instant feedback
                    const memoryItemElement = deleteButton.closest('.memory-item');
                    if (memoryItemElement) memoryItemElement.remove();
                    
                    // Check if list is now empty
                    if (memoriesListContainer.childElementCount === 0 || 
                        (memoriesListContainer.childElementCount === 1 && memoriesListContainer.firstChild.classList.contains('memories-view-feedback'))) {
                        memoriesEmpty.style.display = 'block';
                        deleteAllMemoriesButton.disabled = true;
                    }
                    // Optionally: await loadUserMemories(); // For full refresh, but slower
                } catch (error) {
                    // Error message is handled by apiCall and addSystemMessageToMemoriesView
                    deleteButton.disabled = false; // Re-enable on error
                }
            }
        }
    });

    deleteAllMemoriesButton.addEventListener('click', async () => {
        if (!currentUserId || deleteAllMemoriesButton.disabled) return;
        if (confirm('Are you sure you want to delete ALL your memories? This action cannot be undone.')) {
            showButtonLoader(deleteAllMemoriesButton);
            try {
                await apiCall(`/api/memories/by_user/${currentUserId}`, 'DELETE');
                addSystemMessageToMemoriesView("All memories deleted successfully.", "success");
                loadUserMemories(); // Refresh list (should be empty and update button states)
            } catch (error) {
                // Error message handled by apiCall
            } finally {
                hideButtonLoader(deleteAllMemoriesButton);
            }
        }
    });
    // END: MEMORIES FUNCTIONALITY


    // --- RESPONSIVE HANDLING ---
    function handleResize() {
        const previouslyMobile = isMobileView;
        isMobileView = window.innerWidth <= 768;

        if (previouslyMobile !== isMobileView) {
            if (isMobileView) {
                if (!sidebar.classList.contains('closed')) sidebar.classList.add('open');
                sidebar.classList.remove('closed');
            } else {
                if (sidebar.classList.contains('open')) sidebar.classList.remove('closed');
                sidebar.classList.remove('open');
            }
        }
    }
    window.addEventListener('resize', handleResize);

    // --- INITIALIZATION ---
    function init() {
        appContainer.style.opacity = '0';
        userIdModal.classList.add('active');
        userIdInput.focus();
        handleResize(); // Set initial mobile/desktop state for sidebar
        if (!isMobileView) {
            // sidebar.classList.remove('closed'); // Default open on desktop
        } else {
             sidebar.classList.remove('open'); // Ensure closed on mobile if it was open
        }
        deleteAllMemoriesButton.disabled = true; // Initially no memories loaded
    }
    init();
});