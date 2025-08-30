/**
 * BarterHub Main JavaScript
 * Handles client-side functionality for the barter marketplace
 */

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validations
    initializeFormValidations();
    
    // Initialize image previews
    initializeImagePreviews();
    
    // Initialize auto-refresh for chat
    initializeChatAutoRefresh();
    
    // Initialize point calculator
    initializePointCalculator();
    
    // Initialize confirmation dialogs
    initializeConfirmations();
    
    // Initialize search functionality
    initializeSearch();
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize form validations
 */
function initializeFormValidations() {
    // Bootstrap form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Custom validations
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(function(field) {
        field.addEventListener('input', function() {
            validatePasswordStrength(this);
        });
    });

    // Email validation
    const emailFields = document.querySelectorAll('input[type="email"]');
    emailFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            validateEmail(this);
        });
    });
}

/**
 * Validate password strength
 */
function validatePasswordStrength(passwordField) {
    const password = passwordField.value;
    const strengthIndicator = document.getElementById('password-strength');
    
    if (!strengthIndicator) return;
    
    let strength = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 8) strength += 1;
    else feedback.push('Minimal 8 karakter');
    
    // Uppercase check
    if (/[A-Z]/.test(password)) strength += 1;
    else feedback.push('Satu huruf besar');
    
    // Lowercase check
    if (/[a-z]/.test(password)) strength += 1;
    else feedback.push('Satu huruf kecil');
    
    // Number check
    if (/\d/.test(password)) strength += 1;
    else feedback.push('Satu angka');
    
    // Special character check
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 1;
    else feedback.push('Satu karakter khusus');
    
    // Update strength indicator
    const strengthLevels = ['Sangat Lemah', 'Lemah', 'Sedang', 'Kuat', 'Sangat Kuat'];
    const strengthColors = ['danger', 'warning', 'info', 'success', 'success'];
    
    strengthIndicator.className = `badge bg-${strengthColors[strength]}`;
    strengthIndicator.textContent = strengthLevels[strength] || 'Sangat Lemah';
    
    if (feedback.length > 0) {
        strengthIndicator.title = 'Perlu: ' + feedback.join(', ');
    }
}

/**
 * Validate email format
 */
function validateEmail(emailField) {
    const email = emailField.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        emailField.setCustomValidity('Format email tidak valid');
        emailField.classList.add('is-invalid');
    } else {
        emailField.setCustomValidity('');
        emailField.classList.remove('is-invalid');
    }
}

/**
 * Initialize image preview functionality
 */
function initializeImagePreviews() {
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            handleImagePreview(e.target);
        });
    });
}

/**
 * Handle image preview
 */
function handleImagePreview(input) {
    const files = input.files;
    const previewContainer = document.getElementById('image-preview') || createImagePreviewContainer(input);
    
    // Clear existing previews
    previewContainer.innerHTML = '';
    
    if (files.length === 0) return;
    
    // Check file count limit
    if (files.length > 5) {
        showAlert('Maksimal 5 gambar yang dapat diupload', 'warning');
        input.value = '';
        return;
    }
    
    Array.from(files).forEach(function(file, index) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showAlert('File harus berupa gambar', 'danger');
            return;
        }
        
        // Validate file size (16MB)
        if (file.size > 16 * 1024 * 1024) {
            showAlert('Ukuran file maksimal 16MB', 'danger');
            return;
        }
        
        // Create preview
        const reader = new FileReader();
        reader.onload = function(e) {
            const previewItem = createImagePreviewItem(e.target.result, file.name, index === 0);
            previewContainer.appendChild(previewItem);
        };
        reader.readAsDataURL(file);
    });
}

/**
 * Create image preview container
 */
function createImagePreviewContainer(input) {
    const container = document.createElement('div');
    container.id = 'image-preview';
    container.className = 'row g-3 mt-2';
    input.parentNode.appendChild(container);
    return container;
}

/**
 * Create image preview item
 */
function createImagePreviewItem(src, filename, isMain) {
    const col = document.createElement('div');
    col.className = 'col-md-3';
    
    col.innerHTML = `
        <div class="card">
            <img src="${src}" class="card-img-top" style="height: 120px; object-fit: cover;">
            <div class="card-body p-2">
                <small class="text-muted d-block">${filename}</small>
                ${isMain ? '<span class="badge bg-primary">Foto Utama</span>' : ''}
            </div>
        </div>
    `;
    
    return col;
}

/**
 * Initialize chat auto-refresh
 */
function initializeChatAutoRefresh() {
    if (window.location.pathname.includes('/chat/room/')) {
        // Auto-scroll to bottom of messages
        const messagesContainer = document.querySelector('.chat-messages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Auto-refresh every 30 seconds
        setInterval(function() {
            if (document.visibilityState === 'visible') {
                location.reload();
            }
        }, 30000);
    }
}

/**
 * Initialize point calculator
 */
function initializePointCalculator() {
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    
    rangeInputs.forEach(function(range) {
        range.addEventListener('input', function() {
            updateRangeDisplay(this);
            calculateTotalPoints();
        });
        
        // Initialize display
        updateRangeDisplay(range);
    });
    
    // Initial calculation
    calculateTotalPoints();
}

/**
 * Update range display value
 */
function updateRangeDisplay(range) {
    const name = range.name.replace('_score', '');
    const valueDisplay = document.getElementById(name + '-value');
    if (valueDisplay) {
        valueDisplay.textContent = range.value;
    }
}

/**
 * Calculate total points for product
 */
function calculateTotalPoints() {
    const ranges = ['utility_score', 'scarcity_score', 'durability_score', 'portability_score', 'seasonal_score'];
    let total = 0;
    let count = 0;
    
    ranges.forEach(function(rangeName) {
        const range = document.querySelector(`input[name="${rangeName}"]`);
        if (range) {
            total += parseInt(range.value);
            count++;
        }
    });
    
    if (count > 0) {
        const baseScore = total / count;
        
        // Get condition multiplier
        const conditionSelect = document.querySelector('select[name="condition"]');
        let multiplier = 0.8; // default
        
        if (conditionSelect) {
            const conditionMultipliers = {
                'New': 1.0,
                'Like New': 0.9,
                'Good': 0.8,
                'Fair': 0.6,
                'Poor': 0.4
            };
            multiplier = conditionMultipliers[conditionSelect.value] || 0.8;
        }
        
        const totalPoints = Math.round(baseScore * multiplier * 10);
        
        // Update display
        const pointsDisplay = document.getElementById('calculated-points');
        if (pointsDisplay) {
            pointsDisplay.textContent = totalPoints;
        }
    }
}

/**
 * Initialize confirmation dialogs
 */
function initializeConfirmations() {
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Apakah Anda yakin?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                // Auto-submit search after 1 second of inactivity
                if (searchInput.value.length >= 3 || searchInput.value.length === 0) {
                    searchInput.form.submit();
                }
            }, 1000);
        });
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-dynamic');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show alert-dynamic`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert alert at top of main content
    const main = document.querySelector('main') || document.body;
    main.insertBefore(alert, main.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

/**
 * Format currency (Indonesian Rupiah)
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(amount);
}

/**
 * Format date to Indonesian locale
 */
function formatDate(date) {
    return new Intl.DateTimeFormat('id-ID', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

/**
 * Format relative time
 */
function formatRelativeTime(date) {
    const now = new Date();
    const targetDate = new Date(date);
    const diffTime = now - targetDate;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Hari ini';
    } else if (diffDays === 1) {
        return 'Kemarin';
    } else if (diffDays < 7) {
        return `${diffDays} hari yang lalu`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} minggu yang lalu`;
    } else if (diffDays < 365) {
        const months = Math.floor(diffDays / 30);
        return `${months} bulan yang lalu`;
    } else {
        const years = Math.floor(diffDays / 365);
        return `${years} tahun yang lalu`;
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showAlert('Teks berhasil disalin', 'success');
        }).catch(function() {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

/**
 * Fallback copy to clipboard
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showAlert('Teks berhasil disalin', 'success');
    } catch (err) {
        showAlert('Gagal menyalin teks', 'danger');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Debounce function
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Lazy load images
 */
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver(function(entries, observer) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(function(img) {
        imageObserver.observe(img);
    });
}

/**
 * Handle network status
 */
function handleNetworkStatus() {
    function updateOnlineStatus() {
        const status = navigator.onLine ? 'online' : 'offline';
        document.body.className = document.body.className.replace(/(^|\s)(online|offline)(\s|$)/, '$1$3');
        document.body.classList.add(status);
        
        if (!navigator.onLine) {
            showAlert('Koneksi internet terputus. Beberapa fitur mungkin tidak berfungsi.', 'warning');
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
}

/**
 * Initialize progressive enhancement features
 */
function initializeProgressiveEnhancement() {
    // Check for various API support
    const features = {
        geolocation: 'geolocation' in navigator,
        notifications: 'Notification' in window,
        serviceWorker: 'serviceWorker' in navigator,
        webShare: 'share' in navigator
    };
    
    // Store in data attributes for CSS/JS reference
    Object.keys(features).forEach(function(feature) {
        document.documentElement.setAttribute(`data-${feature}`, features[feature]);
    });
}

/**
 * Handle page visibility changes
 */
function handleVisibilityChange() {
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'hidden') {
            // Page is hidden, pause non-essential operations
            console.log('Page hidden - pausing operations');
        } else {
            // Page is visible, resume operations
            console.log('Page visible - resuming operations');
        }
    });
}

// Initialize additional features when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeLazyLoading();
    handleNetworkStatus();
    initializeProgressiveEnhancement();
    handleVisibilityChange();
});

// Export functions for global access
window.BarterHub = {
    showAlert,
    formatCurrency,
    formatDate,
    formatRelativeTime,
    copyToClipboard,
    debounce,
    throttle,
    isInViewport
};
