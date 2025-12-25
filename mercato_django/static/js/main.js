/**
 * MercatoPro - Main JavaScript File
 * Common functionality for all pages
 */

$(document).ready(function() {
    // Initialize all components
    initializeToastr();
    initializeForms();
    initializeCards();
    initializeDropdowns();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
});

/**
 * Initialize Toastr notifications
 */
function initializeToastr() {
    // Check for Django messages and display them as toasts
    {% if messages %}
        {% for message in messages %}
            {% if message.tags == 'success' %}
                toastr.success('{{ message }}');
            {% elif message.tags == 'error' %}
                toastr.error('{{ message }}');
            {% elif message.tags == 'warning' %}
                toastr.warning('{{ message }}');
            {% else %}
                toastr.info('{{ message }}');
            {% endif %}
        {% endfor %}
    {% endif %}
}

/**
 * Initialize form validation and submission
 */
function initializeForms() {
    // Add CSRF token to all AJAX requests
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // Handle form submissions with AJAX
    $('form[data-ajax="true"]').on('submit', function(e) {
        e.preventDefault();
        const $form = $(this);
        const $button = $form.find('button[type="submit"]');
        const originalText = $button.html();
        
        // Show loading state
        $button.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Caricamento...');
        
        $.ajax({
            url: $form.attr('action'),
            type: $form.attr('method') || 'POST',
            data: $form.serialize(),
            success: function(response) {
                if (response.success) {
                    toastr.success(response.message || 'Operazione completata con successo!');
                    if (response.redirect) {
                        window.location.href = response.redirect;
                    }
                } else {
                    toastr.error(response.message || 'Si è verificato un errore.');
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                if (response.errors) {
                    // Display form validation errors
                    $form.find('.is-invalid').removeClass('is-invalid');
                    $form.find('.invalid-feedback').remove();
                    
                    for (const [field, errors] of Object.entries(response.errors)) {
                        const $input = $form.find(`[name="${field}"]`);
                        if ($input.length) {
                            $input.addClass('is-invalid');
                            $input.after(`<div class="invalid-feedback">${errors.join(', ')}</div>`);
                        }
                    }
                    toastr.error('Correggi gli errori nel modulo.');
                } else {
                    toastr.error(response.message || 'Si è verificato un errore durante l\'elaborazione.');
                }
            },
            complete: function() {
                $button.prop('disabled', false).html(originalText);
            }
        });
    });

    // Handle delete confirmations
    $('button[data-confirm-delete]').on('click', function() {
        const url = $(this).data('url');
        const message = $(this).data('message') || 'Sei sicuro di voler eliminare questo elemento?';
        
        if (confirm(message)) {
            $.ajax({
                url: url,
                type: 'DELETE',
                success: function(response) {
                    toastr.success(response.message || 'Elemento eliminato con successo!');
                    if (response.redirect) {
                        window.location.href = response.redirect;
                    } else {
                        location.reload();
                    }
                },
                error: function(xhr) {
                    const response = xhr.responseJSON || {};
                    toastr.error(response.message || 'Si è verificato un errore durante l\'eliminazione.');
                }
            });
        }
    });
}

/**
 * Initialize card interactions
 */
function initializeCards() {
    // Add click-to-copy functionality
    $('.click-to-copy').on('click', function() {
        const text = $(this).data('copy-text') || $(this).text();
        navigator.clipboard.writeText(text).then(function() {
            toastr.success('Copiato negli appunti!');
        });
    });

    // Add expandable card functionality
    $('.card[data-expandable="true"]').on('click', function(e) {
        if (!$(e.target).is('button, a, input')) {
            const $card = $(this);
            const $content = $card.find('.card-content');
            $content.slideToggle(300);
            $card.toggleClass('expanded');
        }
    });
}

/**
 * Initialize dropdown behaviors
 */
function initializeDropdowns() {
    // Prevent dropdown from closing when clicking inside
    $('.dropdown-menu').on('click', function(e) {
        e.stopPropagation();
    });
}

/**
 * Helper function to get CSRF token from cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'EUR') {
    return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('it-IT', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Format datetime
 */
function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('it-IT', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Export functions for use in other scripts
 */
window.MercatoPro = {
    formatCurrency: formatCurrency,
    formatDate: formatDate,
    formatDateTime: formatDateTime,
    debounce: debounce,
    getCookie: getCookie
};
