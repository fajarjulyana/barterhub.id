
/**
 * Enhanced Floating Chat System for BarterHub
 * Real-time chat notifications and messaging
 */

class FloatingChat {
    constructor() {
        this.isOpen = false;
        this.activeChatRoomId = null;
        this.refreshInterval = null;
        this.notificationPermission = 'default';
        this.lastUnreadCount = 0;
        this.chatWindow = null;
        this.chatToggle = null;
        
        this.init();
    }

    init() {
        this.chatWindow = document.getElementById('chatWindow');
        this.chatToggle = document.querySelector('.chat-toggle');
        
        if (!this.chatWindow || !this.chatToggle) return;

        this.requestNotificationPermission();
        this.setupEventListeners();
        this.startAutoRefresh();
        
        // Initial load
        this.loadChatRooms();
    }

    requestNotificationPermission() {
        if ('Notification' in window) {
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    this.notificationPermission = permission;
                });
            } else {
                this.notificationPermission = Notification.permission;
            }
        }
    }

    setupEventListeners() {
        // Toggle chat
        this.chatToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Quick chat form
        const quickChatForm = document.getElementById('quickChatForm');
        if (quickChatForm) {
            quickChatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendQuickMessage();
            });
        }

        // Close chat when clicking outside
        document.addEventListener('click', (e) => {
            if (this.isOpen && !document.getElementById('chatFloat').contains(e.target)) {
                this.close();
            }
        });

        // Handle Enter key in message input
        document.addEventListener('keydown', (e) => {
            if (e.target.id === 'quickMessageInput' && e.key === 'Enter') {
                e.preventDefault();
                this.sendQuickMessage();
            }
        });

        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.loadChatRooms();
                if (this.activeChatRoomId) {
                    this.loadChatMessages(this.activeChatRoomId);
                }
            }
        });
    }

    startAutoRefresh() {
        // Refresh every 15 seconds
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadChatRooms();
                if (this.activeChatRoomId) {
                    this.loadChatMessages(this.activeChatRoomId);
                }
            }
        }, 15000);
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.chatWindow.classList.add('show');
        this.loadChatRooms();
        
        // Add bounce animation to toggle
        this.chatToggle.style.animation = 'none';
    }

    close() {
        this.isOpen = false;
        this.chatWindow.classList.remove('show');
        this.backToChatList();
        
        // Restore bounce animation
        this.chatToggle.style.animation = '';
    }

    async loadChatRooms() {
        try {
            const response = await fetch('/chat/rooms', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (!response.ok) throw new Error('Failed to load chat rooms');
            
            const data = await response.json();
            this.updateChatRoomsList(data.rooms || []);
            this.updateChatBadge(data.total_unread || 0);
            
            // Show notification for new messages
            if (data.has_new_messages && data.total_unread > this.lastUnreadCount) {
                this.showNotification(
                    data.notification_title || 'BarterHub Chat',
                    data.notification_message || 'Pesan baru tersedia'
                );
            }
            
            this.lastUnreadCount = data.total_unread || 0;
            
        } catch (error) {
            console.error('Error loading chat rooms:', error);
            this.showError('Gagal memuat chat rooms');
        }
    }

    updateChatRoomsList(rooms) {
        const container = document.getElementById('chatRoomsList');
        
        if (rooms.length === 0) {
            container.innerHTML = `
                <div class="text-center p-4">
                    <div class="mb-3">
                        <i class="fas fa-comment-dots fs-1 text-muted opacity-50"></i>
                    </div>
                    <h6 class="text-muted">Belum ada chat aktif</h6>
                    <p class="small text-muted mb-3">Mulai chat dengan menawar produk di marketplace!</p>
                    <a href="/products/" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-search me-1"></i>Cari Produk
                    </a>
                </div>
            `;
            return;
        }

        container.innerHTML = rooms.map(room => `
            <div class="chat-room-item ${room.has_recent_activity ? 'has-activity' : ''}" 
                 onclick="floatingChat.openChatRoom(${room.id}, '${room.product_name}', '${room.other_user}')">
                <div class="d-flex align-items-center">
                    <div class="chat-avatar me-3">
                        <i class="fas fa-user"></i>
                        ${room.unread_count > 0 ? '<div class="status-indicator"></div>' : ''}
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <h6 class="mb-1 chat-room-title">${room.other_user}</h6>
                            <div class="text-end">
                                <small class="text-muted">${room.last_message_time}</small>
                                ${room.unread_count > 0 ? `<span class="badge bg-danger rounded-pill ms-1">${room.unread_count}</span>` : ''}
                            </div>
                        </div>
                        <small class="text-primary mb-1 d-block">${room.product_name}</small>
                        <p class="mb-0 chat-last-message">${room.last_message}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateChatBadge(unreadCount) {
        const badge = document.getElementById('chatBadge');
        const toggle = this.chatToggle;
        
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'block';
            
            // Add notification animation to toggle
            toggle.classList.add('has-notification');
            
            // Update browser title
            document.title = `(${unreadCount}) BarterHub - Platform Barter Terpercaya`;
        } else {
            badge.style.display = 'none';
            toggle.classList.remove('has-notification');
            document.title = 'BarterHub - Platform Barter Terpercaya';
        }
    }

    openChatRoom(roomId, productName, otherUser) {
        this.activeChatRoomId = roomId;
        
        // Show active chat view
        document.getElementById('chatRoomsList').style.display = 'none';
        document.getElementById('activeChatView').style.display = 'flex';
        
        // Update header
        document.getElementById('activeChatTitle').textContent = otherUser;
        document.getElementById('activeChatSubtitle').textContent = productName;
        
        // Load messages
        this.loadChatMessages(roomId);
        
        // Set up auto-refresh for this specific chat
        this.setupChatRefresh(roomId);
    }

    setupChatRefresh(roomId) {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            if (this.activeChatRoomId === roomId && document.visibilityState === 'visible') {
                this.loadChatMessages(roomId);
            }
        }, 3000); // Refresh every 3 seconds for active chat
    }

    async loadChatMessages(roomId) {
        try {
            // Get room info first
            const roomResponse = await fetch(`/chat/room_info/${roomId}`);
            const roomData = await roomResponse.json();
            
            if (!roomData.success) throw new Error(roomData.error);
            
            // Get messages
            const messagesResponse = await fetch(`/chat/room/${roomData.product_id}/messages`);
            const messagesData = await messagesResponse.json();
            
            this.updateChatMessages(messagesData.messages || []);
            
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Gagal memuat pesan');
        }
    }

    updateChatMessages(messages) {
        const container = document.getElementById('chatMessagesMini');
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3">
                    <i class="fas fa-comment-dots text-muted fs-4"></i>
                    <p class="mb-0 small text-muted mt-2">Belum ada pesan</p>
                    <small class="text-muted">Mulai percakapan sekarang!</small>
                </div>
            `;
            return;
        }

        // Show last 8 messages
        const recentMessages = messages.slice(-8);
        const currentUserName = '{{ current_user.full_name if current_user.is_authenticated }}';
        
        container.innerHTML = recentMessages.map(msg => {
            const isOwn = msg.sender_name === currentUserName;
            const messageTime = new Date(msg.created_at).toLocaleTimeString('id-ID', {
                hour: '2-digit', 
                minute: '2-digit'
            });
            
            return `
                <div class="message-mini ${isOwn ? 'own-message' : 'other-message'}">
                    <div class="message-bubble-mini">
                        <div class="message-content-mini">${this.escapeHtml(msg.message)}</div>
                        <small class="message-time-mini">${messageTime}</small>
                    </div>
                </div>
            `;
        }).join('');

        // Auto scroll to bottom with smooth animation
        setTimeout(() => {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }

    async sendQuickMessage() {
        const input = document.getElementById('quickMessageInput');
        const message = input.value.trim();
        
        if (!message || !this.activeChatRoomId) return;

        try {
            // Disable input while sending
            input.disabled = true;
            
            // Get room info first
            const roomResponse = await fetch(`/chat/room_info/${this.activeChatRoomId}`);
            const roomData = await roomResponse.json();
            
            if (!roomData.success) throw new Error(roomData.error);
            
            // Send message
            const formData = new FormData();
            formData.append('message', message);
            formData.append('csrf_token', document.querySelector('input[name="csrf_token"]')?.value || '');
            
            const response = await fetch(`/chat/room/${roomData.product_id}`, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            if (!response.ok) throw new Error('Failed to send message');
            
            // Clear input and refresh
            input.value = '';
            
            // Add message to UI immediately (optimistic update)
            this.addOptimisticMessage(message);
            
            // Reload messages after a short delay
            setTimeout(() => this.loadChatMessages(this.activeChatRoomId), 1000);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Gagal mengirim pesan. Coba lagi.');
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    addOptimisticMessage(message) {
        const container = document.getElementById('chatMessagesMini');
        const messageTime = new Date().toLocaleTimeString('id-ID', {
            hour: '2-digit', 
            minute: '2-digit'
        });
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message-mini own-message';
        messageElement.innerHTML = `
            <div class="message-bubble-mini">
                <div class="message-content-mini">${this.escapeHtml(message)}</div>
                <small class="message-time-mini">${messageTime} <i class="fas fa-clock text-warning"></i></small>
            </div>
        `;
        
        container.appendChild(messageElement);
        container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
        });
    }

    backToChatList() {
        document.getElementById('activeChatView').style.display = 'none';
        document.getElementById('chatRoomsList').style.display = 'block';
        this.activeChatRoomId = null;
        
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    openFullChat() {
        if (this.activeChatRoomId) {
            fetch(`/chat/room_info/${this.activeChatRoomId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = `/chat/room/${data.product_id}`;
                }
            });
        }
    }

    showNotification(title, message, icon = '/static/favicon.ico') {
        // Browser notification
        if (this.notificationPermission === 'granted' && document.visibilityState === 'hidden') {
            const notification = new Notification(title, {
                body: message,
                icon: icon,
                badge: icon,
                tag: 'barterhub-chat',
                requireInteraction: false
            });

            notification.onclick = () => {
                window.focus();
                this.open();
                notification.close();
            };

            setTimeout(() => notification.close(), 8000);
        }

        // Visual notification in chat toggle
        this.chatToggle.classList.add('notification-pulse');
        setTimeout(() => {
            this.chatToggle.classList.remove('notification-pulse');
        }, 3000);

        // Sound notification (optional)
        this.playNotificationSound();
    }

    playNotificationSound() {
        try {
            // Create a simple notification sound
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (error) {
            // Sound notification not available
        }
    }

    showError(message) {
        // Show error in chat window
        const container = document.getElementById('chatRoomsList');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show m-2';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        container.insertBefore(errorDiv, container.firstChild);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for backward compatibility
function toggleChat() {
    if (window.floatingChat) {
        window.floatingChat.toggle();
    }
}

function openChatRoom(roomId, productName, otherUser) {
    if (window.floatingChat) {
        window.floatingChat.openChatRoom(roomId, productName, otherUser);
    }
}

function backToChatList() {
    if (window.floatingChat) {
        window.floatingChat.backToChatList();
    }
}

function openFullChat() {
    if (window.floatingChat) {
        window.floatingChat.openFullChat();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('chatFloat')) {
        window.floatingChat = new FloatingChat();
    }
});
