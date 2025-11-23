/**
 * Authentication page functionality.
 */

'use strict';

// Get elements
const container = document.getElementById('auth-container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

// Check if we should show register form on page load
function checkInitialForm() {
    const url = new URL(window.location);
    const mode = url.searchParams.get('mode');
    
    if (mode === 'register') {
        container.classList.add('right-panel-active');
    }
}

// Toggle between login and register forms
if (registerBtn) {
    registerBtn.addEventListener('click', () => {
        container.classList.add('right-panel-active');
    });
}

if (loginBtn) {
    loginBtn.addEventListener('click', () => {
        container.classList.remove('right-panel-active');
    });
}

// Form validation
const loginForm = document.querySelector('.sign-in form');
const registerForm = document.querySelector('.sign-up form');

if (loginForm) {
    loginForm.addEventListener('submit', function(e) {
        const email = this.querySelector('input[name="email"]').value.trim();
        const password = this.querySelector('input[name="password"]').value;
        
        if (!email || !password) {
            e.preventDefault();
            showNotification('Пожалуйста, заполните все поля', 'error');
            return false;
        }
        
        if (!isValidEmail(email)) {
            e.preventDefault();
            showNotification('Пожалуйста, введите корректный email', 'error');
            return false;
        }
    });
}

if (registerForm) {
    registerForm.addEventListener('submit', function(e) {
        const username = this.querySelector('input[name="username"]').value.trim();
        const email = this.querySelector('input[name="email"]').value.trim();
        const password = this.querySelector('input[name="password"]').value;
        const passwordConfirm = this.querySelector('input[name="password_confirm"]').value;
        const privacyAccepted = this.querySelector('input[name="privacy_accepted"]').checked;
        
        // Validation
        if (!username || !email || !password || !passwordConfirm) {
            e.preventDefault();
            showNotification('Пожалуйста, заполните все поля', 'error');
            return false;
        }
        
        if (!isValidEmail(email)) {
            e.preventDefault();
            showNotification('Пожалуйста, введите корректный email', 'error');
            return false;
        }
        
        if (password !== passwordConfirm) {
            e.preventDefault();
            showNotification('Пароли не совпадают', 'error');
            return false;
        }
        
        if (password.length < 6) {
            e.preventDefault();
            showNotification('Пароль должен быть не менее 6 символов', 'error');
            return false;
        }
        
        if (!privacyAccepted) {
            e.preventDefault();
            showNotification('Вы должны принять политику конфиденциальности', 'error');
            return false;
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    checkInitialForm();
});
