// Custom JavaScript for ProFTPD Admin

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Confirm deletion dialogs
    var deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            var itemName = this.getAttribute('data-item-name') || '此項目';
            if (confirm('確定要刪除 "' + itemName + '" 嗎？此操作無法復原。')) {
                window.location.href = this.href;
            }
        });
    });

    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Password strength indicator
    var passwordInput = document.getElementById('new_password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            var password = this.value;
            var strength = calculatePasswordStrength(password);
            updatePasswordStrengthIndicator(strength);
        });
    }

    // Auto-refresh for monitoring pages
    if (document.body.classList.contains('monitoring-page')) {
        setInterval(function() {
            refreshMonitoringData();
        }, 30000); // Refresh every 30 seconds
    }
});

// Password strength calculation
function calculatePasswordStrength(password) {
    var score = 0;
    if (password.length >= 8) score++;
    if (password.match(/[a-z]/)) score++;
    if (password.match(/[A-Z]/)) score++;
    if (password.match(/[0-9]/)) score++;
    if (password.match(/[^a-zA-Z0-9]/)) score++;
    return score;
}

function updatePasswordStrengthIndicator(strength) {
    var indicator = document.getElementById('password-strength');
    if (!indicator) return;

    var classes = ['bg-danger', 'bg-warning', 'bg-info', 'bg-success'];
    var texts = ['很弱', '弱', '中等', '強', '很強'];
    
    indicator.className = 'progress-bar ' + (classes[Math.min(strength - 1, 3)] || 'bg-secondary');
    indicator.style.width = (strength * 20) + '%';
    indicator.textContent = texts[strength] || '無';
}

// Refresh monitoring data
function refreshMonitoringData() {
    fetch('/monitoring/api/current_stats')
        .then(response => response.json())
        .then(data => {
            updateMonitoringDisplay(data);
        })
        .catch(error => {
            console.error('Failed to refresh monitoring data:', error);
        });
}

function updateMonitoringDisplay(data) {
    // Update connection count
    var connCount = document.getElementById('connection-count');
    if (connCount) {
        connCount.textContent = data.connections || '0';
    }

    // Update disk usage
    var diskUsage = document.getElementById('disk-usage');
    if (diskUsage) {
        diskUsage.textContent = data.disk_usage || 'N/A';
    }
}

// Utility function for AJAX requests
function makeRequest(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: data ? JSON.stringify(data) : null
    });
}

function getCSRFToken() {
    var token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Permission matrix helpers
function toggleAllPermissions(checkbox, type) {
    var checkboxes = document.querySelectorAll('input[name$="' + type + '"]');
    checkboxes.forEach(function(cb) {
        cb.checked = checkbox.checked;
    });
}

// File upload helpers
function validateFileUpload(input, allowedTypes = [], maxSize = 5242880) {
    var file = input.files[0];
    if (!file) return true;

    // Check file type
    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
        alert('不支援的檔案類型');
        input.value = '';
        return false;
    }

    // Check file size (default 5MB)
    if (file.size > maxSize) {
        alert('檔案大小超過限制');
        input.value = '';
        return false;
    }

    return true;
}

// Search and filter functionality
function filterTable(searchInput, tableId) {
    var filter = searchInput.value.toLowerCase();
    var table = document.getElementById(tableId);
    var rows = table.getElementsByTagName('tr');

    for (var i = 1; i < rows.length; i++) {
        var row = rows[i];
        var cells = row.getElementsByTagName('td');
        var found = false;

        for (var j = 0; j < cells.length; j++) {
            var cell = cells[j];
            if (cell.textContent.toLowerCase().indexOf(filter) > -1) {
                found = true;
                break;
            }
        }

        row.style.display = found ? '' : 'none';
    }
}