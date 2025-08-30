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

        // Only load chat rooms if user is authenticated
        const userAuthMeta = document.querySelector('meta[name="user-authenticated"]');
        if (userAuthMeta && userAuthMeta.content === 'true') {
            this.loadChatRooms();
        } else {
            // Hide chat for unauthenticated users
            this.updateChatRoomsList([]);
            this.updateChatBadge(0);
        }
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
                const message = e.target.value ? e.target.value.trim() : '';
                if (message && message !== '') {
                    this.sendQuickMessage();
                } else {
                    this.showError('Pesan tidak boleh kosong');
                    e.target.focus();
                }
            }
        });

        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                console.log('Page visible - resuming operations');
                // Only load chat rooms if user is authenticated
                const userAuthMeta = document.querySelector('meta[name="user-authenticated"]');
                if (userAuthMeta && userAuthMeta.content === 'true') {
                    this.loadChatRooms();
                    if (this.activeChatRoomId) {
                        this.loadChatMessages(this.activeChatRoomId);
                    }
                }
            } else {
                console.log('Page hidden - pausing operations');
            }
        });
    }

    startAutoRefresh() {
        // Refresh every 15 seconds
        setInterval(() => {
            if (document.visibilityState === 'visible') {
                // Only load chat rooms if user is authenticated
                const userAuthMeta = document.querySelector('meta[name="user-authenticated"]');
                if (userAuthMeta && userAuthMeta.content === 'true') {
                    this.loadChatRooms();
                    if (this.activeChatRoomId) {
                        this.loadChatMessages(this.activeChatRoomId);
                    }
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
        // Only load chat rooms if user is authenticated
        const userAuthMeta = document.querySelector('meta[name="user-authenticated"]');
        if (userAuthMeta && userAuthMeta.content === 'true') {
            this.loadChatRooms();
        } else {
            // Show login message for unauthenticated users
            this.updateChatRoomsList([]);
            this.showError('Silakan login untuk menggunakan fitur chat.');
        }

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
                headers: { 
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // User not authenticated
                    this.updateChatRoomsList([]);
                    this.updateChatBadge(0);
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn('Server returned non-JSON response, possibly redirected to login');
                this.updateChatRoomsList([]);
                this.updateChatBadge(0);
                return;
            }

            const data = await response.json();

            // Handle authentication error gracefully
            if (data.success === false && data.error === 'User not authenticated') {
                this.updateChatRoomsList([]);
                this.updateChatBadge(0);
                return;
            }

            if (data.success && data.rooms !== undefined) {
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
            } else {
                console.error('Invalid response structure:', data);
                this.updateChatRoomsList([]);
                this.updateChatBadge(0);
            }

        } catch (error) {
            console.error('Error loading chat rooms:', error);
            // Don't clear rooms on temporary network errors
            if (this.lastUnreadCount === 0) {
                this.updateChatRoomsList([]);
                this.updateChatBadge(0);
            }
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

        container.innerHTML = rooms.map(room => {
            // Tampilkan badge role untuk memberikan konteks yang jelas
            const roleIcon = room.is_product_owner ? 
                '<i class="fas fa-store text-success" title="Anda pemilik produk"></i>' : 
                '<i class="fas fa-shopping-cart text-primary" title="Anda pembeli"></i>';

            return `
                <div class="chat-room-item ${room.has_recent_activity ? 'has-activity' : ''}"
                     onclick="floatingChat.openChatRoom(${room.id}, '${room.product_name}', '${room.other_user}')">
                    <div class="d-flex align-items-center">
                        <div class="chat-avatar me-3">
                            <i class="fas fa-user"></i>
                            ${room.unread_count > 0 ? '<div class="status-indicator"></div>' : ''}
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-start">
                                <h6 class="mb-1 chat-room-title">
                                    ${room.other_user}
                                    <small class="ms-1">${roleIcon}</small>
                                </h6>
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
            `;
        }).join('');
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
            const roomResponse = await fetch(`/chat/room_info/${roomId}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!roomResponse.ok) throw new Error('Failed to fetch room info');
            const roomData = await roomResponse.json();

            if (!roomData.success) throw new Error(roomData.error || 'Failed to get room info');

            // Get messages using room ID directly instead of product ID
            const messagesResponse = await fetch(`/chat/room/${roomId}/messages_direct`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!messagesResponse.ok) throw new Error('Failed to fetch messages');
            const messagesData = await messagesResponse.json();

            this.updateChatMessages(messagesData.messages || []);

        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError(`Gagal memuat pesan: ${error.message}`);
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
                    <div class="mt-3">
                        <button class="btn btn-warning btn-sm" onclick="window.floatingChat.showOfferPanel()">
                            <i class="fas fa-handshake me-1"></i>Buat Penawaran
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        // Show last 8 messages
        const recentMessages = messages.slice(-8);
        const currentUserName = document.querySelector('meta[name="user-full-name"]')?.content || 'Unknown';

        container.innerHTML = recentMessages.map(msg => {
            const isOwn = msg.sender_name === currentUserName;
            const messageTime = new Date(msg.created_at).toLocaleTimeString('id-ID', {
                hour: '2-digit',
                minute: '2-digit'
            });

            // Make sure message content is properly handled
            const messageContent = msg.message && msg.message !== 'undefined' && msg.message !== null && msg.message.trim() !== '' ? msg.message : 'Pesan tidak dapat ditampilkan';

            if (msg.message_type === 'offer') {
                return `
                    <div class="message-mini offer-message">
                        <div class="offer-bubble-mini bg-warning-subtle border border-warning rounded p-2 mb-2">
                            <div class="offer-header d-flex justify-content-between align-items-center mb-1">
                                <small class="fw-bold text-warning">
                                    <i class="fas fa-handshake me-1"></i>
                                    ${isOwn ? 'Penawaran Anda' : 'Penawaran Masuk'}
                                </small>
                                <small class="text-muted">${messageTime}</small>
                            </div>
                            <div class="offer-content small mb-2">${this.escapeHtml(messageContent)}</div>
                            ${!isOwn ? `
                                <div class="offer-actions d-flex gap-1">
                                    <button class="btn btn-success btn-xs" onclick="window.floatingChat.acceptOffer(${msg.id})">
                                        <i class="fas fa-check"></i> Terima
                                    </button>
                                    <button class="btn btn-outline-danger btn-xs" onclick="window.floatingChat.declineOffer(${msg.id})">
                                        <i class="fas fa-times"></i> Tolak
                                    </button>
                                    <button class="btn btn-outline-warning btn-xs" onclick="window.floatingChat.counterOffer(${msg.id})">
                                        <i class="fas fa-reply"></i> Balas
                                    </button>
                                </div>
                            ` : `
                                <div class="text-muted small">
                                    <i class="fas fa-clock me-1"></i>Menunggu respon...
                                </div>
                            `}
                        </div>
                    </div>
                `;
            } else if (msg.message_type === 'system') {
                return `
                    <div class="message-mini system-message">
                        <div class="system-bubble-mini alert alert-info py-1 px-2 mb-2">
                            <i class="fas fa-info-circle me-1"></i>
                            <small>${this.escapeHtml(messageContent)}</small>
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="message-mini ${isOwn ? 'own-message' : 'other-message'} mb-2">
                        <div class="d-flex ${isOwn ? 'justify-content-end' : 'justify-content-start'}">
                            <div class="message-bubble-mini ${isOwn ? 'bg-primary text-white' : 'bg-light'} rounded p-2" style="max-width: 80%;">
                                <div class="message-content-mini small">${this.escapeHtml(messageContent)}</div>
                                <small class="message-time-mini ${isOwn ? 'text-white-50' : 'text-muted'}">${messageTime}</small>
                            </div>
                        </div>
                    </div>
                `;
            }
        }).join('');

        // Add offer button at the bottom
        const offerButton = document.createElement('div');
        offerButton.className = 'text-center mt-2 border-top pt-2';
        offerButton.innerHTML = `
            <button class="btn btn-warning btn-sm" onclick="window.floatingChat.showOfferPanel()">
                <i class="fas fa-handshake me-1"></i>Buat Penawaran Barter
            </button>
        `;
        container.appendChild(offerButton);

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
        const message = input.value ? input.value.trim() : '';

        if (!message || message === '' || !this.activeChatRoomId) {
            console.log('No message or room ID:', {message, activeChatRoomId: this.activeChatRoomId});

            // Tampilkan pesan error jika input kosong
            if (!message || message === '') {
                this.showError('Pesan tidak boleh kosong');
                input.focus();
            }
            return;
        }

        try {
            // Disable input while sending
            input.disabled = true;

            // Get room info first
            const roomResponse = await fetch(`/chat/room_info/${this.activeChatRoomId}`, {
                headers: { 
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            if (!roomResponse.ok) throw new Error('Failed to fetch room info');

            const roomData = await roomResponse.json();
            if (!roomData.success) throw new Error(roomData.error || 'Failed to get room info');

            // Send message
            const formData = new FormData();
            formData.append('message', message);

            // Get CSRF token from hidden input or meta tag
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                             document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }

            console.log('Sending message:', message, 'to room:', this.activeChatRoomId);

            const response = await fetch(`/chat/room/${this.activeChatRoomId}/send_message`, {
                method: 'POST',
                body: formData,
                headers: { 
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Send message error response:', errorText);
                throw new Error(`HTTP error ${response.status}`);
            }

            const result = await response.json();
            console.log('Send message result:', result);

            if (!result.success) {
                throw new Error(result.error || 'Failed to send message');
            }

            // Clear input and refresh
            input.value = '';

            // Add message to UI immediately for better UX
            this.addOptimisticMessage(message);

            // Trigger immediate refresh for both parties
            this.triggerImmediateRefresh();

            // Also refresh after a short delay to ensure server sync
            setTimeout(() => {
                this.loadChatMessages(this.activeChatRoomId);
                this.loadChatRooms();
            }, 300);

        } catch (error) {
            console.error('Error sending message:', error);
            this.showError(`Gagal mengirim pesan: ${error.message}. Coba lagi.`);
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
            fetch(`/chat/room_info/${this.activeChatRoomId}`, {
                 headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Use the product_id from room info to navigate to correct chat room
                    window.location.href = `/chat/room/${data.product_id}`;
                } else {
                    this.showError(`Gagal membuka chat: ${data.error || 'Info room tidak ditemukan'}`);
                }
            })
            .catch(error => {
                console.error('Error opening full chat:', error);
                this.showError('Gagal membuka chat. Coba lagi.');
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
        if (!container) return; // Exit if container not found

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

    async acceptOffer(messageId) {
        if (!confirm('🤝 Apakah Anda yakin menerima penawaran ini?\n\nSetelah diterima, transaksi akan otomatis dibuat dan kedua pihak harus melanjutkan ke tahap pengiriman.')) {
            return;
        }

        try {
            // Get CSRF token from multiple sources
            let csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                           document.querySelector('[name="csrf_token"]')?.value;

            const headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            };

            // Add CSRF token to headers if available
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/chat/offer/${messageId}/accept`, {
                method: 'POST',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success) {
                this.showNotification(
                    'Deal Berhasil!', 
                    `Transaksi #${data.transaction_id} telah dibuat. Selamat!`
                );

                // Trigger immediate refresh for both parties
                this.triggerImmediateRefresh();

                // Additional refresh to ensure sync
                setTimeout(() => {
                    this.loadChatMessages(this.activeChatRoomId);
                    this.loadChatRooms();
                }, 500);

                // Optionally open transaction page
                if (confirm('Apakah Anda ingin melihat detail transaksi sekarang?')) {
                    window.open(`/transactions/${data.transaction_id}`, '_blank');
                }
            } else {
                throw new Error(data.error || 'Gagal menerima penawaran');
            }
        } catch (error) {
            console.error('Error accepting offer:', error);
            alert(`❌ Gagal menerima penawaran: ${error.message}\n\nSilakan coba lagi atau hubungi admin jika masalah berlanjut.`);
        }
    }

    async declineOffer(messageId) {
        const reason = prompt('💬 Alasan menolak penawaran (opsional):\n\nContoh: "Harga kurang sesuai", "Produk tidak sesuai kebutuhan", dll.');

        try {
            // Get CSRF token from multiple sources
            let csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                           document.querySelector('[name="csrf_token"]')?.value;

            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };

            // Add CSRF token to headers if available
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch(`/chat/offer/${messageId}/decline`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({reason: reason || ''})
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.success) {
                this.showNotification('Penawaran Ditolak', data.message || 'Penawaran berhasil ditolak');

                // Trigger immediate refresh for both parties
                this.triggerImmediateRefresh();

                // Additional refresh to ensure sync
                setTimeout(() => {
                    this.loadChatMessages(this.activeChatRoomId);
                    this.loadChatRooms();
                }, 500);
            } else {
                throw new Error(data.error || 'Gagal menolak penawaran');
            }
        } catch (error) {
            console.error('Error declining offer:', error);
            alert(`❌ Gagal menolak penawaran: ${error.message}\n\nSilakan coba lagi.`);
        }
    }

    showQuickNegotiation() {
        // Show negotiation quick buttons in floating chat
        const container = document.getElementById('chatMessagesMini');
        if (!container) return; // Exit if container not found

        const negotiationPanel = document.createElement('div');
        negotiationPanel.className = 'negotiation-quick-panel p-2 border-top';
        negotiationPanel.innerHTML = `
            <div class="text-center mb-2">
                <small class="text-muted"><i class="fas fa-handshake me-1"></i>Aksi Cepat</small>
            </div>
            <div class="d-grid gap-1">
                <button class="btn btn-warning btn-sm" onclick="window.floatingChat.quickSendMessage('Saya tertarik untuk barter. Bisa nego?')">
                    <i class="fas fa-handshake me-1"></i>Tawar Barter
                </button>
                <button class="btn btn-info btn-sm" onclick="window.floatingChat.quickSendMessage('Apakah produk masih tersedia?')">
                    <i class="fas fa-question-circle me-1"></i>Tanya Ketersediaan
                </button>
                <button class="btn btn-success btn-sm" onclick="window.floatingChat.quickSendMessage('Saya setuju dengan deal ini!')">
                    <i class="fas fa-check me-1"></i>Setuju Deal
                </button>
            </div>
        `;

        const chatWindow = document.getElementById('chatWindow');
        const existingPanel = chatWindow.querySelector('.negotiation-quick-panel');
        if (existingPanel) {
            existingPanel.remove();
        }
        chatWindow.appendChild(negotiationPanel);
    }

    quickSendMessage(message) {
        const input = document.getElementById('quickMessageInput');
        if (input && message && message.trim() !== '') {
            input.value = message;
            input.focus();
            // Auto-submit after user can see the message
            setTimeout(() => {
                this.sendQuickMessage();
            }, 500);
        } else {
            this.showError('Template pesan tidak valid');
        }
    }

    showOfferPanel() {
        if (!this.activeChatRoomId) {
            alert('Pilih chat room terlebih dahulu');
            return;
        }

        // Create offer modal
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'quickOfferModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-handshake me-2"></i>Buat Penawaran Barter
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <h6 class="text-success">
                                    <i class="fas fa-box me-1"></i>Produk yang Anda Tawarkan
                                </h6>
                                <div id="offerProductsList" class="mb-3">
                                    <div class="text-center text-muted py-3">
                                        <i class="fas fa-spinner fa-spin"></i> Memuat produk...
                                    </div>
                                </div>
                                <button type="button" class="btn btn-outline-success btn-sm" onclick="window.floatingChat.addOfferProduct()">
                                    <i class="fas fa-plus me-1"></i>Tambah Produk
                                </button>
                            </div>
                            <div class="col-md-6">
                                <h6 class="text-info">
                                    <i class="fas fa-heart me-1"></i>Produk yang Anda Inginkan
                                </h6>
                                <div id="requestProductsList">
                                    <div class="request-item p-2 border rounded mb-2">
                                        <input type="text" class="form-control form-control-sm mb-2" placeholder="Nama produk yang diinginkan..." required>
                                        <textarea class="form-control form-control-sm" rows="2" placeholder="Deskripsi detail..."></textarea>
                                    </div>
                                </div>
                                <button type="button" class="btn btn-outline-info btn-sm" onclick="window.floatingChat.addRequestProduct()">
                                    <i class="fas fa-plus me-1"></i>Tambah Keinginan
                                </button>
                            </div>
                        </div>
                        <div class="mt-3">
                            <label class="form-label">Pesan Penawaran</label>
                            <textarea class="form-control" id="offerMessage" rows="3" 
                                      placeholder="Tulis pesan untuk melengkapi penawaran Anda..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Batal</button>
                        <button type="button" class="btn btn-warning" onclick="window.floatingChat.submitOffer()">
                            <i class="fas fa-handshake me-1"></i>Kirim Penawaran
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Load user products
        this.loadUserProductsForOffer();

        // Clean up modal when closed
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    async loadUserProductsForOffer() {
        try {
            const response = await fetch('/products/user/available');
            const data = await response.json();

            const container = document.getElementById('offerProductsList');
            if (data.success && data.products.length > 0) {
                container.innerHTML = data.products.map(product => `
                    <div class="form-check border rounded p-2 mb-2">
                        <input class="form-check-input" type="checkbox" value="${product.id}" 
                               id="product${product.id}" data-points="${product.total_points}">
                        <label class="form-check-label w-100" for="product${product.id}">
                            <div class="d-flex align-items-center">
                                <img src="/static/uploads/products/${product.main_image}" 
                                     class="me-2 rounded" style="width: 40px; height: 40px; object-fit: cover;"
                                     onerror="this.src='/static/img/default-product.jpg'">
                                <div class="flex-grow-1">
                                    <div class="fw-semibold">${product.title}</div>
                                    <small class="text-muted">${product.condition} • ${product.total_points} poin</small>
                                </div>
                            </div>
                        </label>
                    </div>
                `).join('');
            } else {
                container.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="fas fa-box-open"></i>
                        <p>Belum ada produk tersedia</p>
                        <a href="/products/add" class="btn btn-primary btn-sm">
                            <i class="fas fa-plus"></i> Tambah Produk
                        </a>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading user products:', error);
        }
    }

    addOfferProduct() {
        // This will add more product selectors if needed
        alert('Fitur tambah produk multiple akan segera hadir!');
    }

    addRequestProduct() {
        const container = document.getElementById('requestProductsList');
        const div = document.createElement('div');
        div.className = 'request-item p-2 border rounded mb-2';
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div class="flex-grow-1">
                    <input type="text" class="form-control form-control-sm mb-2" placeholder="Nama produk yang diinginkan..." required>
                    <textarea class="form-control form-control-sm" rows="2" placeholder="Deskripsi detail..."></textarea>
                </div>
                <button type="button" class="btn btn-outline-danger btn-sm ms-2" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(div);
    }

    async submitOffer() {
        if (!this.activeChatRoomId) {
            alert('Chat room tidak ditemukan');
            return;
        }

        const message = document.getElementById('offerMessage').value.trim();
        const selectedProducts = [];
        const requestedItems = [];

        // Collect offered products
        document.querySelectorAll('#offerProductsList input[type="checkbox"]:checked').forEach(checkbox => {
            selectedProducts.push({
                product_id: parseInt(checkbox.value),
                points: parseInt(checkbox.dataset.points),
                quantity: 1
            });
        });

        // Collect requested items
        document.querySelectorAll('#requestProductsList .request-item').forEach(item => {
            const nameInput = item.querySelector('input[type="text"]');
            const descTextarea = item.querySelector('textarea');
            const quantityInput = item.querySelector('input[type="number"]');
            const conditionSelect = item.querySelector('select');

            const name = nameInput ? nameInput.value.trim() : '';
            const description = descTextarea ? descTextarea.value.trim() : '';
            const quantity = quantityInput ? parseInt(quantityInput.value) || 1 : 1;
            const condition = conditionSelect ? conditionSelect.value : '';

            if (name) {
                requestedItems.push({
                    name: name,
                    description: description,
                    quantity: quantity,
                    condition: condition
                });
            }
        });

        // Validasi - minimal ada penawaran atau permintaan
        if (selectedProducts.length === 0 && requestedItems.length === 0) {
            alert('Minimal pilih produk yang ditawarkan atau tulis permintaan produk');
            return;
        }

        try {
            const offerData = {
                message: message || 'Penawaran barter',
                offered_products: selectedProducts,
                requested_products: requestedItems
            };

            const response = await fetch(`/chat/room/${this.activeChatRoomId}/send_negotiation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(offerData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            if (result.success) {
                // Close modal
                const modal = document.getElementById('quickOfferModal');
                if (modal && bootstrap.Modal.getInstance(modal)) {
                    bootstrap.Modal.getInstance(modal).hide();
                }

                // Show success message
                this.showNotification('Penawaran Dikirim', result.message || 'Penawaran berhasil dikirim!');

                // Refresh messages and rooms
                setTimeout(() => {
                    this.loadChatMessages(this.activeChatRoomId);
                    this.loadChatRooms();
                }, 500);

            } else {
                throw new Error(result.error || 'Gagal mengirim penawaran');
            }
        } catch (error) {
            console.error('Error submitting offer:', error);
            alert('Gagal mengirim penawaran: ' + error.message + '. Silakan coba lagi.');
        }
    }

    counterOffer(messageId) {
        // Show offer panel for counter offer
        this.showOfferPanel();
        // Pre-fill with counter offer context
        setTimeout(() => {
            const messageInput = document.getElementById('offerMessage');
            if (messageInput) {
                messageInput.value = 'Counter offer untuk penawaran sebelumnya:';
            }
        }, 500);
    }

    // Method to trigger an immediate refresh of chat rooms and messages
    // This is intended to be called after sending a message or performing an action
    // that should immediately update the chat view for both parties.
    triggerImmediateRefresh() {
        console.log('Triggering immediate refresh...');
        if (document.visibilityState === 'visible') {
            // Reload chat rooms to get the latest unread counts and activity status
            this.loadChatRooms();

            // If an active chat room is open, reload its messages
            if (this.activeChatRoomId) {
                this.loadChatMessages(this.activeChatRoomId);
            }
        }
    }
}

// Initialize floating chat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Assuming 'initializeFloatingChat' is a function that creates an instance of FloatingChat
    // and attaches it to the window object, like window.floatingChat = new FloatingChat();
    // If the original code had a specific initialization function, it should be called here.
    // For now, we'll assume the class constructor handles initialization as per the original code.
    if (document.getElementById('chatFloat')) {
        window.floatingChat = new FloatingChat();
    }
});

// Global functions for external access (added from changes)
// Note: These global functions are exposed to the global scope for external use, e.g., from product detail pages.
// They assume the existence of `isAuthenticated`, `chatWidget`, `chatRooms`, `loadChatRooms`, `selectChatRoom`, and `initializeFloatingChat`
// which are not defined within this scope but are implied by the provided changes.
// For this to work, these external dependencies need to be properly defined in the HTML or other JS files.

// Mock implementations for context, assuming these would be defined elsewhere:
const isAuthenticated = document.querySelector('meta[name="user-authenticated"]')?.content === 'true';
const chatWidget = document.getElementById('chatWindow');
let chatRooms = []; // This would be populated by loadChatRooms()

function initializeFloatingChat() {
    // This function is assumed to be responsible for creating the FloatingChat instance
    // and assigning it to window.floatingChat. The DOMContentLoaded listener already does this.
    // If there were other initializations, they would go here.
}

// Mock functions for the new global functions to operate
async function loadChatRooms() {
    // Placeholder: In a real scenario, this would fetch and update the chatRooms array.
    // For demonstration, we'll simulate a fetch.
    try {
        const response = await fetch('/chat/rooms', {
            headers: { 
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        const data = await response.json();
        if (data.rooms) {
            chatRooms = data.rooms;
        }
    } catch (error) {
        console.error('Mock loadChatRooms failed:', error);
    }
}

function selectChatRoom(roomId) {
    const room = chatRooms.find(r => r.id === roomId);
    if (room && window.floatingChat) {
        window.floatingChat.openChatRoom(room.id, room.product_name, room.other_user);
    } else {
        console.error('Room not found or floatingChat not initialized.');
    }
}

// Global functions for backward compatibility (kept from original code)
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

// --- New Global functions from the changes ---
// These are exposed to the global scope for external use, e.g., from product detail pages.
window.FloatingChat = {
    openChatForProduct: function(productId, sellerName) {
        if (!isAuthenticated) {
            alert('Silakan login terlebih dahulu untuk menggunakan chat.');
            return;
        }

        // Open floating chat if it's closed
        if (chatWidget && !chatWidget.classList.contains('show')) {
            chatWidget.classList.add('show');
        }

        // Find or create chat room for this product
        // This part requires the FloatingChat instance to be initialized and available globally.
        // It also assumes that the /chat/room/{productId} endpoint is available and works as expected.
        fetch(`/chat/room/${productId}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.ok) {
                // The response from /chat/room/{productId} might create the room and return room details.
                // We then need to find this room in our list or load messages to display it.
                loadChatRooms().then(() => {
                    // After potentially creating or confirming the room, find it in the loaded list.
                    const room = chatRooms.find(r => r.product_id == productId);
                    if (room) {
                        selectChatRoom(room.id); // Use the selected room to open the chat view
                    } else {
                        // If the room wasn't immediately available in the list,
                        // try fetching messages directly for the product to ensure it's loaded/created.
                        fetch(`/chat/room/${productId}/messages`) // Assuming this endpoint also ensures room creation/loading
                            .then(msgResponse => {
                                if (msgResponse.ok) {
                                    // Reload rooms again to ensure the newly created/accessed room is in our list
                                    loadChatRooms().then(() => {
                                        const newRoom = chatRooms.find(r => r.product_id == productId);
                                        if (newRoom) {
                                            selectChatRoom(newRoom.id);
                                        } else {
                                            console.error('Failed to find newly created chat room.');
                                            alert('Gagal membuka chat. Ruangan chat tidak ditemukan.');
                                        }
                                    });
                                } else {
                                    throw new Error('Failed to fetch messages for new room');
                                }
                            })
                            .catch(error => {
                                console.error('Error creating or loading chat room messages:', error);
                                alert('Gagal membuka chat. Silakan coba lagi.');
                            });
                    }
                });
            } else {
                throw new Error('Failed to access or create chat room');
            }
        })
        .catch(error => {
            console.error('Error opening chat for product:', error);
            alert('Gagal membuka chat. Silakan coba lagi.');
        });
    },

    toggleChat: function() {
        if (chatWidget) {
            chatWidget.classList.toggle('show');
        }
    }
};