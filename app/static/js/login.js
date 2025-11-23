/**
 * Login/Register form toggle functionality
 */

'use strict';

document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('container');
  const registerBtn = document.getElementById('register');
  const loginBtn = document.getElementById('login');

  if (registerBtn) {
    registerBtn.addEventListener('click', () => {
      container.classList.add('active');
    });
  }

  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      container.classList.remove('active');
    });
  }

  // Close flash messages after 5 seconds
  const flashMessages = document.querySelectorAll('.flash-messages .flash');
  flashMessages.forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity 0.3s ease';
      setTimeout(() => flash.remove(), 300);
    }, 5000);
  });
});
