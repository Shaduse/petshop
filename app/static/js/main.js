/**
 * Main JavaScript for PetShop
 * Handles slider functionality and general interactions
 */

'use strict';

// ============================================================================
// BREED DETECT LOGIC
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('fileInput');
    const fileSelectBtn = document.getElementById('fileSelectBtn');
    const dropArea = document.getElementById('drop-area');
    const imagePreview = document.getElementById('image-preview');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const removeImageBtn = document.getElementById('removeImageBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsContainer = document.getElementById('results-container');
    const errorMessage = document.getElementById('error-message');
    const recommendationsList = document.getElementById('recommendations-list');

    if (!dropArea) return; // Выходим, если мы не на странице breed-detect

    let uploadedFile = null;

    // --- Вспомогательные функции ---
    function showMessage(text, type = 'danger') {
        errorMessage.textContent = text;
        errorMessage.className = `alert alert-${type} mt-3`;
        errorMessage.style.display = 'block';
    }

    function hideMessage() {
        errorMessage.style.display = 'none';
    }

    function showLoading(show) {
        loadingSpinner.style.display = show ? 'block' : 'none';
        analyzeBtn.disabled = show;
        analyzeBtn.innerHTML = show ? '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Анализ...' : '<i class="fas fa-paw"></i> Определить породу';
    }

    function resetUI() {
        uploadedFile = null;
        fileInput.value = '';
        imagePreviewContainer.style.display = 'none';
        dropArea.style.display = 'block';
        analyzeBtn.disabled = true;
        resultsContainer.style.display = 'none';
        document.getElementById('recommendations-block').style.display = 'none';
        recommendationsList.innerHTML = '';
        hideMessage();
    }

    function displayFile(file) {
        uploadedFile = file;
        const reader = new FileReader();
        reader.onload = function (e) {
            imagePreview.src = e.target.result;
            imagePreviewContainer.style.display = 'block';
            dropArea.style.display = 'none';
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function handleFiles() {
        if (!fileInput.files.length) return;
        const file = fileInput.files[0];

        // Проверка размера (5 МБ)
        if (file.size > 5 * 1024 * 1024) {
            showMessage('Файл слишком большой! Максимум 5 МБ.');
            resetUI();
            return;
        }
        
        if (!file.type.startsWith('image/')) {
            showMessage('Недопустимый формат файла. Выберите изображение.');
            resetUI();
            return;
        }

        displayFile(file);
    }

    // --- Обработчики событий ---

    // 1. Клик по кнопке "Выберите файл"
    fileSelectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
    });

    // 2. Клик по всей зоне тоже открывает выбор файла
    dropArea.addEventListener('click', (e) => {
        // Проверяем, что клик не был на самой кнопке, чтобы избежать двойного открытия
        if (e.target.id !== 'fileSelectBtn') {
            fileInput.click();
        }
    });

    // 3. Drag and Drop
    dropArea.addEventListener('dragover', e => { e.preventDefault(); dropArea.classList.add('highlight'); });
    dropArea.addEventListener('dragleave', () => dropArea.classList.remove('highlight'));
    dropArea.addEventListener('drop', e => {
        e.preventDefault();
        dropArea.classList.remove('highlight');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFiles();
        }
    });

    // 4. Обработка выбора файла (через кнопку или drag&drop)
    fileInput.addEventListener('change', handleFiles);

    // 5. Удаление фото
    removeImageBtn.addEventListener('click', resetUI);

    // 6. Analyze Button
    analyzeBtn.addEventListener('click', analyzeImage);

    // --- AJAX Логика ---
    function analyzeImage() {
        if (!uploadedFile) {
            showMessage('Пожалуйста, загрузите изображение.');
            return;
        }

        hideMessage();
        showLoading(true);
        resultsContainer.style.display = 'none';

        const formData = new FormData();
        formData.append('file', uploadedFile);

        fetch('/breed-detect', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; }).catch(() => {
                    throw new Error('Ошибка сервера. Попробуйте позже.');
                });
            }
            return response.json();
        })
        .then(data => {
            showLoading(false);
            if (data.success) {
                updateResults(data.breed_data, data.recommendations, data.recommendation_title);
            } else {
                showMessage(data.message || 'Не удалось определить породу.');
            }
        })
        .catch(error => {
            showLoading(false);
            console.error('Fetch Error:', error);
            showMessage(error.message || 'Произошла непредвиденная ошибка.');
        });
    }

    function updateResults(breedData, recommendations, recommendationTitle) {
        const recommendedBreedNameEl = document.getElementById('recommended-breed-name');
        const recommendationsTitleEl = document.getElementById('recommendations-title');
        const recommendationsBlock = document.getElementById('recommendations-block');
        
        document.getElementById('breed-name').textContent = breedData.breed_name;
        document.getElementById('confidence-score').textContent = breedData.confidence;
        document.getElementById('breed-description').textContent = breedData.description;
        
        // Обновление заголовка рекомендаций
        recommendedBreedNameEl.textContent = recommendationTitle;
        
        // Обновление рекомендаций
        recommendationsList.innerHTML = '';
        if (recommendations && recommendations.length > 0) {
            recommendations.forEach(item => {
                const card = `
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 shadow-sm">
                            <a href="${item.url}" class="text-decoration-none text-dark">
                                <img src="${item.image}" class="card-img-top" alt="${item.name}" style="height: 200px; object-fit: cover;">
                            </a>
                            <div class="card-body d-flex flex-column">
                                <h5 class="card-title">${item.name}</h5>
                                <p class="card-text text-primary fw-bold">${formatPrice(item.price)}</p>
                                <div class="mt-auto d-flex justify-content-between">
                                    <a href="${item.url}" class="btn btn-sm btn-outline-primary">Подробнее</a>
                                    <button type="button" class="btn btn-sm btn-success add-to-cart-btn" data-product-id="${item.id}">В корзину</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                recommendationsList.insertAdjacentHTML('beforeend', card);
            });
            recommendationsBlock.style.display = 'block';
        } else {
            // Скрываем блок рекомендаций, если нет товаров
            recommendationsBlock.style.display = 'none';
        }

        resultsContainer.style.display = 'block';
    }

    // Инициализация
    resetUI();
});

// ============================================================================
// HERO SLIDER
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
  const slides = document.querySelectorAll('.slide');
  const dots = document.querySelectorAll('.dot');
  const prevBtn = document.querySelector('.prev-btn');
  const nextBtn = document.querySelector('.next-btn');
  let currentSlide = 0;
  let autoSlideInterval;

  // Show specific slide
  function showSlide(n) {
    if (slides.length === 0) return;
    
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    
    currentSlide = (n + slides.length) % slides.length;
    
    slides[currentSlide].classList.add('active');
    if (dots[currentSlide]) {
      dots[currentSlide].classList.add('active');
    }
  }

  // Next slide
  function nextSlide() {
    showSlide(currentSlide + 1);
  }

  // Previous slide
  function prevSlide() {
    showSlide(currentSlide - 1);
  }

  // Start auto slide
  function startAutoSlide() {
    autoSlideInterval = setInterval(nextSlide, 5000);
  }

  // Stop auto slide
  function stopAutoSlide() {
    clearInterval(autoSlideInterval);
  }

  // Initialize slider if slides exist
  if (slides.length > 0) {
    startAutoSlide();

    // Button click handlers
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        stopAutoSlide();
        nextSlide();
        startAutoSlide();
      });
    }
    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        stopAutoSlide();
        prevSlide();
        startAutoSlide();
      });
    }

    // Dot click handlers
    dots.forEach((dot, index) => {
      dot.addEventListener('click', () => {
        stopAutoSlide();
        showSlide(index);
        startAutoSlide();
      });
    });

    // Pause on hover
    const sliderContainer = document.querySelector('.hero-slider');
    if (sliderContainer) {
      sliderContainer.addEventListener('mouseenter', stopAutoSlide);
      sliderContainer.addEventListener('mouseleave', startAutoSlide);
    }
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

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Format price with currency
 */
function formatPrice(price) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(price);
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
  const container = document.getElementById('notification-container');
  if (!container) return;

  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;

  container.appendChild(notification);

  setTimeout(() => {
    notification.classList.add('show');
  }, 10);

  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      notification.remove();
    }, 500);
  }, 5000);
}

// ============================================================================
// CART QUANTITY UPDATE (AJAX) — ИСПРАВЛЕННАЯ ВЕРСИЯ
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {

    // Обработка + / -
    document.querySelectorAll('.btn-plus, .btn-minus').forEach(button => {
        button.addEventListener('click', function () {
            const cartItemId = this.dataset.cartItemId;
            const input = document.querySelector(`#quantity-${cartItemId}`);
            let quantity = parseInt(input.value) || 1;

            if (this.classList.contains('btn-plus')) {
                quantity += 1;
            } else if (this.classList.contains('btn-minus')) {
                quantity -= 1;
                if (quantity < 1) quantity = 1;
            }

            input.value = quantity;
            updateCartItem(cartItemId, quantity);
        });
    });

    // Ручной ввод количества
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function () {
            let quantity = parseInt(this.value) || 1;
            if (quantity < 1) {
                quantity = 1;
                this.value = 1;
            }
            const cartItemId = this.dataset.cartItemId;
            updateCartItem(cartItemId, quantity);
        });
    });

    // Основная функция обновления
    function updateCartItem(cartItemId, quantity) {
        const input = document.querySelector(`#quantity-${cartItemId}`);
        const initialValue = parseInt(input.dataset.initialValue);

        if (quantity === initialValue) return;

        fetch(`/cart/update/${cartItemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ quantity: quantity })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Защита от undefined
                const itemTotal = data.item_total ?? 0;
                const cartTotal = data.cart_total ?? 0;

                // Обновляем строку товара
                const itemTotalEl = document.getElementById(`item-total-${cartItemId}`);
                if (itemTotalEl) {
                    itemTotalEl.textContent = `${formatPrice(itemTotal)} ₽`;
                }

                // Обновляем общую сумму
                const subtotalEl = document.getElementById('subtotal-amount');
                const totalEl = document.getElementById('total-amount');
                if (subtotalEl) subtotalEl.textContent = `${formatPrice(cartTotal)} ₽`;
                if (totalEl) totalEl.textContent = `${formatPrice(cartTotal)} ₽`;

                // Обновляем начальное значение
                input.dataset.initialValue = quantity;

                // Уведомление
                if (typeof showNotification === 'function') {
                    showNotification('Корзина обновлена', 'success');
                }
            } else {
                alert(data.message || 'Ошибка обновления корзины');
                location.reload();
            }
        })
        .catch(err => {
            console.error('Cart update error:', err);
            alert('Ошибка связи с сервером. Обновляем страницу...');
            location.reload();
        });
    }
});