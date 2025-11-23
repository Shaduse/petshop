from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import timedelta
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, User, Product, Category, Order, OrderItem, CartItem, Favorite, Address, Review, Subscriber, OrderStatus, Breed, product_breeds, Role, PromoCode, PromoCodeCampaign
from functools import wraps
from slugify import slugify
from app.email import send_verification_email, send_password_reset_email, generate_verification_code, send_order_confirmation_email, send_promo_code_email, send_mass_promo_code_email, send_subscription_verification_email
import time
from image_processor import process_product_image
import os
from PIL import Image
from io import BytesIO
import json
import os.path
import secrets
from datetime import datetime, timezone
import google.generativeai as genai
from google.generativeai import types


def permission_required(permission):
    """Decorator for routes requiring a specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission):
                flash('У вас нет прав доступа.', 'error')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def moderator_required(f):
    """Decorator for moderator-only routes (deprecated, use permission_required)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Fallback for old code, check for a common permission like 'manage_products'
        if not current_user.is_authenticated or not current_user.has_permission('manage_products'):
            flash('У вас нет прав доступа.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for admin-only routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated and has the 'Admin' role
        if not current_user.is_authenticated or not current_user.has_role('Admin'):
            flash('У вас нет прав доступа.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function for Russian grammar (Roditelny padezh - Genitive case)
def to_genitive(breed_name):
    """Simple heuristic to convert a breed name to the genitive case for 'Рекомендуем для...'"""
    if breed_name.endswith('а'):
        return breed_name[:-1] + 'ы'
    elif breed_name.endswith('я'):
        return breed_name[:-1] + 'и'
    elif breed_name.endswith('ь'):
        return breed_name[:-1] + 'я'
    elif breed_name.endswith('р') or breed_name.endswith('н'):
        return breed_name + 'а'
    elif breed_name.endswith('ий'):
        return breed_name[:-2] + 'ого'
    elif breed_name.endswith('ая'):
        return breed_name[:-2] + 'ой'
    elif breed_name.endswith('ий'):
        return breed_name[:-2] + 'ого'
    return breed_name # Fallback

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
product_bp = Blueprint('product', __name__, url_prefix='/product')
profile_bp = Blueprint('profile', __name__, url_prefix='/profile')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        login_input = request.form.get('email', '').strip()  # This field now accepts both email and username
        password = request.form.get('password', '')

        if not login_input or not password:
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('auth.login'))

        # Try to find user by email first, then by username
        user = User.query.filter_by(email=login_input).first()
        if not user:
            user = User.query.filter_by(username=login_input).first()

        if user and user.check_password(password):
            if not user.is_verified:
                flash('Пожалуйста, подтвердите вашу почту.', 'warning')
                return redirect(url_for('auth.verify_email', email=user.email))

            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Неверный логин или пароль.', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        privacy_accepted = request.form.get('privacy_accepted')
        
        # Validation
        if not all([username, email, password, password_confirm]):
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('auth.register'))
        
        if password != password_confirm:
            flash('Пароли не совпадают.', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'error')
            return redirect(url_for('auth.register'))
        
        if not privacy_accepted:
            flash('Вы должны принять политику конфиденциальности.', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято.', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Эта почта уже зарегистрирована.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User(
            username=username,
            email=email,
            privacy_accepted=True,
            privacy_accepted_at=datetime.now(timezone.utc),
            is_verified=True  # Auto-verify for immediate login
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Auto-login after registration
        login_user(user)
        flash('Регистрация успешна! Вы вошли в аккаунт.', 'success')

        return redirect(url_for('main.index'))
    
    return render_template('auth/register.html')


@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Email verification route."""
    email = request.args.get('email', '') or request.form.get('email', '')
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if not code:
            flash('Пожалуйста, введите код подтверждения.', 'error')
            return redirect(url_for('auth.verify_email', email=email))
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Пользователь не найден.', 'error')
            return redirect(url_for('auth.login'))
        
        # For demo: accept any 6-digit code
        if len(code) == 6 and code.isdigit():
            user.is_verified = True
            user.verification_token = None
            db.session.commit()
            flash('Почта успешно подтверждена! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Неверный код подтверждения.', 'error')
            return redirect(url_for('auth.verify_email', email=email))
    
    return render_template('auth/verify_email.html', email=email)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request route."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate and send password reset code
            reset_code = generate_verification_code()
            user.verification_token = reset_code
            # Set expiration time (e.g., 15 minutes)
            user.verification_token_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.session.commit()

            if send_password_reset_email(email, reset_code):
                flash('Код для сброса пароля отправлен на вашу почту.', 'success')
            else:
                flash('Произошла ошибка при отправке кода. Попробуйте позже.', 'error')
            
            return redirect(url_for('auth.verify_reset_code', email=email))
        else:
            flash('Пользователь с таким email не найден.', 'error')
            return redirect(url_for('auth.forgot_password'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/verify-reset-code', methods=['GET', 'POST'])
def verify_reset_code():
    """Password reset code verification route."""
    email = request.args.get('email', '') or request.form.get('email', '')
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        
        if not code:
            flash('Пожалуйста, введите код подтверждения.', 'error')
            return redirect(url_for('auth.verify_reset_code', email=email))
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Пользователь не найден.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check code and expiration
        # Ensure comparison is between timezone-aware objects
        token_expires_aware = user.verification_token_expires.replace(tzinfo=timezone.utc)
        if user.verification_token == code and token_expires_aware > datetime.now(timezone.utc):
            # Code is valid, redirect to password reset form
            # Generate a temporary, single-use token for the final reset step
            temp_token = secrets.token_urlsafe(32)
            user.verification_token = temp_token # Reuse the field for the final reset token
            user.verification_token_expires = datetime.now(timezone.utc) + timedelta(minutes=5) # Short expiration for final step
            db.session.commit()
            
            return redirect(url_for('auth.reset_password', token=temp_token))
        else:
            flash('Неверный или просроченный код подтверждения.', 'error')
            return redirect(url_for('auth.verify_reset_code', email=email))
    
    # GET request
    return render_template('auth/verify_reset_code.html', email=email)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Final password reset route."""
    token = request.args.get('token', '')
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if not password or not password_confirm:
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        if password != password_confirm:
            flash('Пароли не совпадают.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        user = User.query.filter_by(verification_token=token).first()
        
        # Ensure comparison is between timezone-aware objects
        token_expires_aware = user.verification_token_expires.replace(tzinfo=timezone.utc)
        if not user or token_expires_aware < datetime.now(timezone.utc):
            flash('Неверная или просроченная ссылка для сброса пароля.', 'error')
            return redirect(url_for('auth.login'))
        
        # Reset password
        user.set_password(password)
        user.verification_token = None
        user.verification_token_expires = None
        db.session.commit()
        
        flash('Ваш пароль успешно изменен. Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    
    # GET request
    user = User.query.filter_by(verification_token=token).first()
    
    # Ensure comparison is between timezone-aware objects
    token_expires_aware = user.verification_token_expires.replace(tzinfo=timezone.utc)
    if not user or token_expires_aware < datetime.now(timezone.utc):
        flash('Неверная или просроченная ссылка для сброса пароля.', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/resend-verification')
def resend_verification():
    """Resend verification code."""
    email = request.args.get('email', '')
    user = User.query.filter_by(email=email).first()

    if user:
        # Generate and send new verification code
        verification_code = generate_verification_code()
        user.verification_token = verification_code
        user.verification_token_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.session.commit()

        if send_verification_email(email, verification_code):
            flash('Код подтверждения отправлен на вашу почту.', 'success')
        else:
            flash('Произошла ошибка при отправке кода. Попробуйте позже.', 'error')
    else:
        flash('Пользователь не найден.', 'error')

    return redirect(url_for('auth.verify_email', email=email))


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))


# ============================================================================
# MAIN ROUTES
# ============================================================================

def is_subscribed_cookie_set(email):
    """Проверяет, установлена ли кука подписки для данного email."""
    return request.cookies.get(f'subscribed_{email}') == 'true'

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Home page."""
        # Fetch recommended products (e.g., first 8 marked as recommended)
    recommended_products = Product.query.filter_by(is_active=True, is_recommended=True).limit(8).all()
    
    # Fetch popular categories (e.g., all marked as popular)
    popular_categories = Category.query.filter_by(is_active=True, is_popular=True).order_by(Category.display_order).all()
    
    # Fallback for general products and categories
    if not recommended_products:
        recommended_products = Product.query.filter_by(is_active=True).limit(8).all()
        
    if not popular_categories:
        popular_categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    
    # Проверка статуса подписки для текущего пользователя
    is_subscribed = False
    if current_user.is_authenticated:
        subscriber = Subscriber.query.filter_by(email=current_user.email, is_verified=True).first()
        is_subscribed = subscriber is not None
        
    return render_template("index.html", 
                           recommended_products=recommended_products, 
                           popular_categories=popular_categories, 
                           is_subscribed=is_subscribed)


@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html', title='О нас')

@main_bp.route('/breed-detect', methods=['GET', 'POST'])
@login_required
def breed_detect():
    """Pet breed detection page."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Файл не найден.'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Файл не выбран.'}), 400
            
        if file:
            try:
                # 1. Чтение файла и преобразование в объект PIL Image
                image_data = file.read()
                img = Image.open(BytesIO(image_data))
                
                # Конвертация в RGB (если есть альфа-канал) и затем в JPEG в памяти для совместимости с Gemini
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                    
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)
                
                # Переоткрываем как PIL Image из байтов JPEG для передачи в Gemini
                img = Image.open(img_byte_arr)
                
                # 2. Инициализация Gemini
                # Ключ API берется из переменной окружения GEMINI_API_KEY
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

                # 3. Запрос к Gemini
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = """
                    Ты эксперт по породам кошек и собак. Проанализируй изображение.
                    Определи породу животного на фото и его тип (кошка или собака).
                    Твоя задача - дать максимально точный и профессиональный ответ.
                    Если на изображении не кошка и не собака, или изображение нечеткое,
                    ты должен это указать в поле "description".

                    Ответь строго в формате JSON, используя следующую структуру:
                    {
                        "pet_type": "собака" или "кошка" или "Неизвестно",
                        "breed_name": "Название породы (например, Лабрадор-ретривер)",
                        "confidence": "Уверенность в процентах (например, 95%)",
                        "description": "Профессиональное описание породы или анализ изображения (2-3 предложения)"
                    }

                    Если животное не определено как кошка или собака, используй "Неизвестно" для pet_type, "Неизвестно" для breed_name и 0% для confidence.
                    """

                response = model.generate_content(
                    [prompt, img],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                    ),
                )
                
                # 4. Парсинг ответа
                result_data = json.loads(response.text)
                
                # 5. Поиск рекомендаций
                breed_name = result_data['breed_name']
                breed_name_slug = slugify(breed_name)
                pet_type = result_data.get('pet_type', 'Неизвестно')
                
                # Улучшенная обработка "Неизвестно"
                if pet_type == 'Неизвестно' or breed_name_slug == 'неизвестно':
                    # Возвращаем специальный ответ для "Неизвестно"
                    return jsonify({
                        'success': True,
                        'breed_data': {
                            'pet_type': 'Неизвестно',
                            'breed_name': 'Неизвестно',
                            'confidence': '0%',
                            'description': 'На изображении не удалось определить кошку или собаку. Пожалуйста, загрузите другое фото вашего питомца.'
                        },
                        'recommendations': [],
                        'recommendation_title': 'Неизвестного питомца'
                    })
                
                # Поиск породы в базе данных
                breed = Breed.query.filter_by(slug=breed_name_slug).first()
                
                recommendations = []
                
                # 5.1. Поиск по породе
                if breed:
                    # Ищем товары, привязанные к этой породе
                    recommended_products = Product.query.join(product_breeds).filter(product_breeds.c.breed_id == breed.id).limit(6).all()
                    
                    for product in recommended_products:
                        recommendations.append({
                            'id': product.id,
                            'name': product.name,
                            'price': int(product.price),
                            'image': product.image or '/static/img/placeholder.jpg',
                            'url': url_for('product.view', product_id=product.id)
                        })
                
                # 5.2. Поиск по типу животного (если нет рекомендаций по породе)
                if not recommendations and pet_type != 'Неизвестно':
                    # Ищем товары, привязанные к любой породе данного типа
                    pet_type_breeds = Breed.query.filter_by(pet_type=pet_type).all()
                    pet_type_breed_ids = [b.id for b in pet_type_breeds]
                    
                    if pet_type_breed_ids:
                        # Ищем товары, связанные с породами данного типа
                        recommended_products = Product.query.join(product_breeds).filter(product_breeds.c.breed_id.in_(pet_type_breed_ids)).limit(6).all()
                        
                        for product in recommended_products:
                            recommendations.append({
                                'id': product.id,
                                'name': product.name,
                                'price': int(product.price),
                                'image': product.image or '/static/img/placeholder.jpg',
                                'url': url_for('product.view', product_id=product.id)
                            })
                    
                    # Если даже по типу животного не нашлось, ищем по категории (например, "Корма для кошек")
                    if not recommendations:
                        category_slug = slugify(f'{pet_type}-food') # Например, 'cat-food'
                        category = Category.query.filter_by(slug=category_slug).first()
                        if category:
                            recommended_products = Product.query.filter_by(category_id=category.id).limit(6).all()
                            for product in recommended_products:
                                recommendations.append({
                                    'id': product.id,
                                    'name': product.name,
                                    'price': int(product.price),
                                    'image': product.image or '/static/img/placeholder.jpg',
                                    'url': url_for('product.view', product_id=product.id)
                                })
                
                # 5.3. Поиск общих товаров (если все еще нет рекомендаций)
                if not recommendations:
                    # Ищем 6 любых товаров
                    general_products = Product.query.limit(6).all()
                    for product in general_products:
                        recommendations.append({
                            'id': product.id,
                            'name': product.name,
                            'price': int(product.price),
                            'image': product.image or '/static/img/placeholder.jpg',
                            'url': url_for('product.view', product_id=product.id)
                        })
                
                # Формирование заголовка для рекомендаций
                if breed_name and breed_name != 'Неизвестно':
                    # Порода определена, используем родительный падеж
                    recommendation_title = to_genitive(breed_name)
                elif pet_type == 'собака':
                    recommendation_title = 'вашей собаки'
                elif pet_type == 'кошка':
                    recommendation_title = 'вашей кошки'
                else:
                    # Fallback, хотя это не должно случиться, если pet_type не "Неизвестно"
                    recommendation_title = 'вашего питомца'
                
                return jsonify({
                    'success': True,
                    'breed_data': result_data,
                    'recommendations': recommendations,
                    'recommendation_title': recommendation_title
                })
                
            except Exception as e:
                print(f"Gemini Error: {e}")
                return jsonify({'success': False, 'message': f'Ошибка при анализе фото: {str(e)}'}), 500
        else:
            return jsonify({'success': False, 'message': 'Недопустимый формат файла.'}), 400
            
    return render_template('breed_detect.html', title='Определение породы')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}
    
@main_bp.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')

# ============================================================================
# PRODUCT ROUTES
# ============================================================================

@product_bp.route('/list')
def list_products():
    """Product listing page."""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '').strip()
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.paginate(page=page, per_page=12)
    categories = Category.query.all()
    
    return render_template('products/list.html', products=products, categories=categories, search=search)


@product_bp.route('/<int:product_id>')
def view(product_id):
    """Product detail page."""
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id, is_approved=True).all()
    
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first() is not None
    
    return render_template('products/detail.html', product=product, reviews=reviews, is_favorite=is_favorite)


@product_bp.route('/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    """Add product review."""
    product = Product.query.get_or_404(product_id)

    rating = request.form.get('rating', type=float)
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    if not rating or rating < 1.0 or rating > 5.0:
        flash('Неверная оценка.', 'error')
        return redirect(url_for('product.view', product_id=product_id))

    # Check if user already reviewed
    existing_review = Review.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing_review:
        existing_review.rating = rating
        existing_review.title = title
        existing_review.content = content
        existing_review.updated_at = datetime.now(timezone.utc)
    else:
        review = Review(
            product_id=product_id,
            user_id=current_user.id,
            rating=rating, is_approved=False,
            title=title,
            content=content
        )
        db.session.add(review)

    db.session.commit()
    flash('Отзыв добавлен успешно.', 'success')
    return redirect(url_for('product.view', product_id=product_id))




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


# ============================================================================
# CART ROUTES
# ============================================================================

@main_bp.route('/cart')
def view_cart():
    """View shopping cart."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('cart/view.html', cart_items=cart_items, total=total)


@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """Add product to cart."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    product = Product.query.get_or_404(product_id)
    quantity = request.form.get('quantity', 1, type=int)
    
    if quantity < 1:
        quantity = 1
    
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Товар добавлен в корзину.', 'success')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/cart/apply_promo', methods=['POST'])
@login_required
def apply_promo_code():
    """Apply a promo code to the cart."""
    code = request.form.get('promo_code', '').strip().upper()
    
    if not code:
        flash('Пожалуйста, введите промокод.', 'error')
        return redirect(url_for('main.view_cart'))
        
    promo_code = PromoCode.query.filter_by(code=code, is_active=True).first()
    
    if not promo_code:
        flash('Неверный или неактивный промокод.', 'error')
        return redirect(url_for('main.view_cart'))
        
    # Check max uses
    if promo_code.max_uses != -1 and promo_code.current_uses >= promo_code.max_uses:
        flash('Срок действия промокода истек (достигнуто максимальное количество использований).', 'error')
        return redirect(url_for('main.view_cart'))
        
    # Check validity period
    now = datetime.now(timezone.utc)
    if promo_code.valid_until and now > promo_code.valid_until.replace(tzinfo=timezone.utc):
        flash('Срок действия промокода истек.', 'error')
        return redirect(url_for('main.view_cart'))
        
    # Store promo code in session for use at checkout
    session['promo_code'] = code
    
    flash(f'Промокод "{code}" успешно применен! Скидка будет рассчитана при оформлении заказа.', 'success')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/cart/update/<int:cart_item_id>', methods=['POST'])
@login_required
def update_cart_item(cart_item_id):
    """Update item quantity in cart."""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    
    if cart_item.user_id != current_user.id:
        is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({'success': False, 'message': 'Доступ запрещен.'}), 403
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('main.view_cart'))
        
    quantity = request.form.get('quantity', type=int)
    
    # Если это AJAX-запрос с JSON, получаем quantity из request.json
    if quantity is None and request.is_json and request.json:
        json_quantity = request.json.get('quantity')
        if json_quantity is not None:
            try:
                quantity = int(json_quantity)
            except ValueError:
                # Если не удалось преобразовать в int, оставляем None, чтобы сработала проверка ниже
                quantity = None
    
    if quantity is None or quantity < 1:
        is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify({'success': False, 'message': 'Неверное количество.'}), 400
        flash('Неверное количество.', 'error')
        return redirect(url_for('main.view_cart'))
        
    cart_item.quantity = quantity
    db.session.commit()
    
    # Calculate new totals
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    
    # Assuming fixed shipping and tax logic from checkout route
    # NOTE: The original template shows only subtotal and total, with shipping "calculated at checkout".
    # We will use the subtotal for the final total for simplicity, as the original template does.
    # If shipping/tax logic is needed, it should be consistent with the checkout route.
    # For now, we assume total = subtotal as per the visual in the original template.
    total = subtotal
    
    # Проверяем, является ли запрос AJAX (по заголовку X-Requested-With или Content-Type: application/json)
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax:
        return jsonify({
            'success': True,
            'item_total': int(cart_item.product.price * quantity),
            'cart_total': int(subtotal)
        })
    
    flash('Количество товара обновлено.', 'success')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/cart/remove/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    """Remove item from cart."""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    
    if cart_item.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('main.view_cart'))
        
    db.session.delete(cart_item)
    db.session.commit()
    
    flash('Товар удален из корзины.', 'success')
    return redirect(url_for('main.view_cart'))


@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout process: select address and confirm order."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Ваша корзина пуста.', 'warning')
        return redirect(url_for('main.view_cart'))

    # Calculate totals
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_cost = 300.00 # Example fixed shipping cost
    tax = round(subtotal * 0.05, 2) # Example 5% tax
    total = subtotal + shipping_cost + tax
    
    # Apply promo code if present in session
    promo_code_obj = None
    discount_amount = 0.0
    promo_code_str = session.get('promo_code')
    
    if promo_code_str:
        promo_code_obj = PromoCode.query.filter_by(code=promo_code_str, is_active=True).first()
        
        if promo_code_obj:
            # Check max uses
            if promo_code_obj.max_uses != -1 and promo_code_obj.current_uses >= promo_code_obj.max_uses:
                promo_code_obj = None # Invalidate if max uses reached
            
            # Check validity period
            now = datetime.now(timezone.utc)
            if promo_code_obj and promo_code_obj.valid_until and now > promo_code_obj.valid_until.replace(tzinfo=timezone.utc):
                promo_code_obj = None # Invalidate if expired
                
            if promo_code_obj:
                if promo_code_obj.discount_type == 'percent':
                    discount_amount = round(total * (promo_code_obj.discount_value / 100.0), 2)
                elif promo_code_obj.discount_type == 'fixed':
                    discount_amount = promo_code_obj.discount_value
                
                # Ensure discount does not exceed total
                if discount_amount > total:
                    discount_amount = total
                    
                total -= discount_amount
                total = round(total, 2)
                
                flash(f'Применена скидка по промокоду "{promo_code_str}": -{discount_amount} ₽', 'info')
            else:
                flash(f'Промокод "{promo_code_str}" недействителен или истек.', 'error')
                session.pop('promo_code', None) # Remove invalid code from session
        else:
            session.pop('promo_code', None) # Remove invalid code from session
    
    # Store discount in session for POST request
    session['discount_amount'] = discount_amount
    session['promo_code_id'] = promo_code_obj.id if promo_code_obj else None

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        address_id = request.form.get('address_id', type=int)
        notes = request.form.get('notes', '').strip()
        
        if not address_id:
            flash('Пожалуйста, выберите адрес доставки.', 'error')
            return redirect(url_for('main.checkout'))
        
        address = Address.query.get(address_id)
        if not address or address.user_id != current_user.id:
            flash('Неверный адрес доставки.', 'error')
            return redirect(url_for('main.checkout'))

        # Retrieve discount from session
        discount_amount = session.pop('discount_amount', 0.0)
        promo_code_id = session.pop('promo_code_id', None)
        
        # Recalculate total to ensure consistency (should match GET request logic)
        subtotal_post = sum(item.product.price * item.quantity for item in cart_items)
        shipping_cost_post = 300.00
        tax_post = round(subtotal_post * 0.05, 2)
        total_post = subtotal_post + shipping_cost_post + tax_post - discount_amount
        total_post = round(total_post, 2)
        
        # Increment promo code usage if used
        if promo_code_id:
            promo_code_obj = PromoCode.query.get(promo_code_id)
            if promo_code_obj:
                promo_code_obj.current_uses += 1
        
        # Create Order
        order_number = secrets.token_hex(8).upper() # Simple unique order number
        
        new_order = Order(
            user_id=current_user.id,
            address_id=address.id,
            order_number=order_number,
            subtotal=subtotal_post,
            shipping_cost=shipping_cost_post,
            tax=tax_post,
            total=total_post,
            promo_code_id=promo_code_id,
            discount_amount=discount_amount,
            notes=notes,
            status=OrderStatus.PENDING
        )
        db.session.add(new_order)
        db.session.flush() # Get order ID

        # Move Cart Items to Order Items
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                product_name=item.product.name, # <-- ДОБАВЛЕНО
                quantity=item.quantity,
                price=item.product.price, # Save price at time of order
                subtotal=item.product.price * item.quantity # Calculate subtotal for item
            )
            db.session.add(order_item)
            db.session.delete(item) # Remove from cart

        db.session.commit()
        
        # Send order confirmation email
        send_order_confirmation_email(new_order)
        
        flash(f'Заказ №{order_number} успешно оформлен!', 'success')
        return redirect(url_for('main.order_confirmation', order_id=new_order.id))

    return render_template('cart/checkout.html', 
                           cart_items=cart_items, 
                           subtotal=subtotal, 
                           shipping_cost=shipping_cost, 
                           tax=tax, 
                           total=total, 
                           addresses=addresses)


@main_bp.route('/order-confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page."""
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('main.index'))
    
    
    @main_bp.route('/verify-subscription')
    def verify_subscription():
        """Verify newsletter subscription."""
        token = request.args.get('token', '')
    
        if not token:
            flash('Неверная ссылка подтверждения.', 'error')
            return redirect(url_for('main.index'))
    
        subscriber = Subscriber.query.filter_by(verification_token=token).first()
    
        if not subscriber:
            flash('Подписчик не найден.', 'error')
            return redirect(url_for('main.index'))
    
        # Check if token is expired
        if subscriber.verification_token_expires and subscriber.verification_token_expires < datetime.now(timezone.utc):
            flash('Ссылка подтверждения истекла. Подпишитесь заново.', 'error')
            return redirect(url_for('main.index'))
    
        # Verify the subscriber
        subscriber.is_verified = True
        subscriber.verified_at = datetime.now(timezone.utc)
        subscriber.verification_token = None
        subscriber.verification_token_expires = None
        db.session.commit()
    
        # Generate and send promo code
        promo_code_str = secrets.token_urlsafe(8).upper()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        promo_code = PromoCode(
            code=promo_code_str,
            discount_type='percent',
            discount_value=10.0,
            max_uses=1,
            valid_until=expires_at
        )
        db.session.add(promo_code)
        db.session.commit()
    
        # Send welcome email with promo code
        if send_promo_code_email(subscriber.email, promo_code_str):
            flash('Подписка подтверждена! Промокод отправлен на вашу почту.', 'success')
        else:
            flash('Подписка подтверждена! Промокод сохранён, но не удалось отправить письмо.', 'warning')
    
        return redirect(url_for('main.index'))
    
    return render_template('cart/confirmation.html', order=order)


# ============================================================================
# PROFILE ROUTES
# ============================================================================

@profile_bp.route('/')
@login_required
def view_profile():
    """View user profile."""
    return render_template('profile/view.html', user=current_user)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        current_user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Профиль обновлен.', 'success')
        return redirect(url_for('profile.view_profile'))
    
    return render_template('profile/edit.html', user=current_user)


@profile_bp.route('/orders')
@login_required
def view_orders():
    """View user orders."""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile/orders.html', orders=orders)


@profile_bp.route('/order/<int:order_id>')
@login_required
def view_order_detail(order_id):
    """View user order detail."""
    order = Order.query.get_or_404(order_id)
    
    # Security check: ensure the order belongs to the current user
    if order.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('profile.view_orders'))
    
    return render_template('profile/order_detail.html', order=order)


@profile_bp.route('/addresses', methods=['GET', 'POST'])
@login_required
def manage_addresses():
    """Manage user addresses."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        street = request.form.get('street', '').strip()
        city = request.form.get('city', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        
        if not all([full_name, phone, street, city]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('profile.manage_addresses'))
        
        address = Address(
            user_id=current_user.id,
            full_name=full_name,
            phone=phone,
            street=street,
            city=city,
            postal_code=postal_code
        )
        db.session.add(address)
        db.session.commit()
        flash('Адрес добавлен.', 'success')
        return redirect(url_for('profile.manage_addresses'))
    
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('profile/addresses.html', addresses=addresses)


@profile_bp.route('/address/delete/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    """Delete a user address."""
    address = Address.query.get_or_404(address_id)
    
    if address.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('profile.manage_addresses'))
    
    # Check if the address is used in any order
    if Order.query.filter_by(address_id=address_id).first():
        flash('Невозможно удалить адрес, так как он используется в одном или нескольких заказах.', 'error')
        return redirect(url_for('profile.manage_addresses'))
        
    db.session.delete(address)
    db.session.commit()
    flash('Адрес удален.', 'success')
    
    return redirect(url_for('profile.manage_addresses'))


@profile_bp.route('/address/edit/<int:address_id>', methods=['GET', 'POST'])
@login_required
def edit_address(address_id):
    """Edit a user address."""
    address = Address.query.get_or_404(address_id)
    
    if address.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('profile.manage_addresses'))
        
    if request.method == 'POST':
        address.full_name = request.form.get('full_name', '').strip()
        address.phone = request.form.get('phone', '').strip()
        address.street = request.form.get('street', '').strip()
        address.city = request.form.get('city', '').strip()
        address.postal_code = request.form.get('postal_code', '').strip()
        
        if not all([address.full_name, address.phone, address.street, address.city]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('profile.edit_address', address_id=address.id))
            
        db.session.commit()
        flash('Адрес обновлен.', 'success')
        return redirect(url_for('profile.manage_addresses'))
        
    # GET request: render form
    return render_template('profile/address_form.html', address=address, form_title='Редактировать адрес')


# ============================================================================
# FAVORITES ROUTES
# ============================================================================

@main_bp.route('/favorite/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_favorites(product_id):
    """Add product to favorites."""
    product = Product.query.get_or_404(product_id)
    
    favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if not favorite:
        favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.session.add(favorite)
        db.session.commit()
        flash('Товар добавлен в избранное.', 'success')
    else:
        flash('Товар уже в избранном.', 'info')
    
    return redirect(request.referrer or url_for('product.view', product_id=product_id))


@main_bp.route('/favorite/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_favorites(product_id):
    """Remove product from favorites."""
    favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404()
    
    db.session.delete(favorite)
    db.session.commit()
    flash('Товар удален из избранного.', 'success')
    return redirect(request.referrer or url_for('main.index'))


@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """User change password route."""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        new_password_confirm = request.form.get('new_password_confirm', '')
        
        if not all([old_password, new_password, new_password_confirm]):
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('profile.change_password'))
        
        if new_password != new_password_confirm:
            flash('Новые пароли не совпадают.', 'error')
            return redirect(url_for('profile.change_password'))
        
        if len(new_password) < 6:
            flash('Новый пароль должен быть не менее 6 символов.', 'error')
            return redirect(url_for('profile.change_password'))
        
        if not current_user.check_password(old_password):
            flash('Неверный текущий пароль.', 'error')
            return redirect(url_for('profile.change_password'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Пароль успешно изменен.', 'success')
        return redirect(url_for('profile.view_profile'))

    return render_template('profile/change_password.html')


@profile_bp.route('/cancel-order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order."""
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('profile.view_orders'))
    
    # Logic for cancellation: only allow if status is 'pending'
    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.CANCELLED
        db.session.commit()
        flash(f'Заказ №{order.order_number} отменен.', 'success')
    else:
        flash(f'Заказ №{order.order_number} не может быть отменен, так как его статус: {order.status.value}.', 'error')
        
    return redirect(url_for('profile.view_order_detail', order_id=order.id))


@profile_bp.route('/return-order/<int:order_id>', methods=['POST'])
@login_required
def return_order(order_id):
    """Request a return for an order."""
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('profile.view_orders'))
    
    # Logic for return: only allow if status is 'delivered'
    if order.status == OrderStatus.DELIVERED:
        # In a real app, this would change the status to 'return_requested' 
        # and notify admin. For now, we'll just flash a message.
        flash(f'Запрос на возврат заказа №{order.order_number} отправлен. Ожидайте связи с менеджером.', 'success')
    else:
        flash(f'Возврат заказа №{order.order_number} невозможен, так как его статус: {order.status.value}.', 'error')
        
    return redirect(url_for('profile.view_order_detail', order_id=order.id))


@profile_bp.route('/favorites')
@login_required
def view_favorites():
    """View user favorites."""
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    products = [fav.product for fav in favorites]
    return render_template('profile/favorites.html', products=products)


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@admin_bp.route('/')
@login_required
def admin_dashboard():
    """Admin dashboard."""
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    
    return render_template('admin/dashboard.html',
                          total_users=total_users,
                          total_products=total_products,
                          total_orders=total_orders,
                          total_revenue=total_revenue)


@admin_bp.route('/orders')
@permission_required('manage_orders')
def admin_orders():
    """Admin orders management."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@admin_bp.route('/order/<int:order_id>')
@permission_required('manage_orders')
def admin_order_detail(order_id):
    """Admin order detail."""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)


@admin_bp.route('/users')
@admin_required
def admin_users():
    """Admin users management."""
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user."""
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()

    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.email = request.form.get('email', '').strip()
        user.phone = request.form.get('phone', '').strip()

        # Handle role assignment
        role_name = request.form.get('role')
        if role_name:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles = [role]  # Assuming one role per user

        # Handle verification
        is_verified = request.form.get('is_verified') == 'on'
        user.is_verified = is_verified

        # Handle password change
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash('Пользователь обновлен.', 'success')
        return redirect(url_for('admin.admin_users'))

    return render_template('admin/user_form.html', user=user, roles=roles)


@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Нельзя удалить самого себя.', 'error')
        return redirect(url_for('admin.admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь "{user.username}" удален.', 'success')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/roles')
@permission_required('manage_users')
def admin_roles():
    """Admin roles management."""
    roles = Role.query.all()

    all_permissions = [
        'manage_categories',
        'manage_reviews',
        'send_mass_emails'
    ]

    return render_template('admin/roles.html', roles=roles, all_permissions=all_permissions)

@admin_bp.route('/role/add', methods=['GET', 'POST'])
@permission_required('manage_users')
def add_role():
    """Add new role."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        permissions = request.form.getlist('permissions')

        if not name:
            flash('Название роли обязательно.', 'error')
            return redirect(url_for('admin.add_role'))

        if Role.query.filter_by(name=name).first():
            flash('Роль с таким названием уже существует.', 'error')
            return redirect(url_for('admin.add_role'))

        role = Role(name=name, description=description)
        role.set_permissions(permissions)
        db.session.add(role)
        db.session.commit()
        flash(f'Роль "{name}" успешно добавлена.', 'success')
        return redirect(url_for('admin.admin_roles'))

    all_permissions = [
        'manage_users',
        'manage_products',
        'manage_orders',
        'manage_promo_codes',
        'manage_categories',
        'manage_reviews',
        'send_mass_emails'
    ]

    return render_template('admin/role_form.html', form_title='Добавить роль', form_action=url_for('admin.add_role'), role=None, all_permissions=all_permissions)


@admin_bp.route('/role/edit/<int:role_id>', methods=['GET', 'POST'])
@permission_required('manage_users')
def edit_role(role_id):
    """Edit existing role."""
    role = Role.query.get_or_404(role_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        permissions = request.form.getlist('permissions')

        if not name:
            flash('Название роли обязательно.', 'error')
            return redirect(url_for('admin.edit_role', role_id=role.id))

        existing_role = Role.query.filter(Role.name == name, Role.id != role.id).first()
        if existing_role:
            flash('Роль с таким названием уже существует.', 'error')
            return redirect(url_for('admin.edit_role', role_id=role.id))

        role.name = name
        role.description = description
        role.set_permissions(permissions)
        db.session.commit()
        flash(f'Роль "{name}" успешно обновлена.', 'success')
        return redirect(url_for('admin.admin_roles'))

    all_permissions = [
        'manage_users',
        'manage_products',
        'manage_orders',
        'manage_promo_codes',
        'manage_categories',
        'manage_reviews',
        'send_mass_emails'
    ]

    return render_template('admin/role_form.html', form_title='Редактировать роль', form_action=url_for('admin.edit_role', role_id=role.id), role=role, all_permissions=all_permissions)


@admin_bp.route('/role/delete/<int:role_id>', methods=['POST'])
@permission_required('manage_users')
def delete_role(role_id):
    """Delete role."""
    role = Role.query.get_or_404(role_id)

    if role.name == 'Admin':
        flash('Нельзя удалить роль Admin.', 'error')
        return redirect(url_for('admin.admin_roles'))

    # Check if any users have this role
    if role.users:
        flash('Нельзя удалить роль, которая назначена пользователям.', 'error')
        return redirect(url_for('admin.admin_roles'))

    db.session.delete(role)
    db.session.commit()
    flash(f'Роль "{role.name}" удалена.', 'success')
    return redirect(url_for('admin.admin_roles'))


@admin_bp.route('/product/add', methods=['GET', 'POST'])
@permission_required('manage_products')
def add_product():
    """Add new product."""
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price')
        stock = request.form.get('stock')
        category_id = request.form.get('category_id')
        image_file = request.files.get('image')
        
        if not all([name, description, price, stock, category_id]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('admin.add_product'))
        
        # Generate slug
        slug = slugify(name) # Simple slug generation
        # Image handling (save to static/uploads and optimize)
        image_url = None
        if image_file and image_file.filename:
            UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'products')
            filename = process_product_image(image_file, UPLOAD_FOLDER, size=(800, 800))
            if filename:
                image_url = url_for('static', filename=f'images/products/{filename}')
            else:
                flash('Ошибка при обработке изображения товара.', 'warning')

        product = Product(
            name=name,
            description=description,
            price=float(price),
            stock=int(stock),
            category_id=int(category_id),
            slug=slug,
            image=image_url
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Товар "{name}" успешно добавлен.', 'success')
        return redirect(url_for('admin.manage_products'))

    return render_template('admin/product_form.html', form_title='Добавить товар', form_action=url_for('admin.add_product'), categories=categories)


@admin_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@permission_required('manage_products')
def edit_product(product_id):
    """Edit existing product."""
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price')
        stock = request.form.get('stock')
        category_id = request.form.get('category_id')
        image_file = request.files.get('image')

        if not all([name, description, price, stock, category_id]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('admin.edit_product', product_id=product.id))

        product.name = name
        product.slug = slugify(name)
        product.description = description
        product.price = float(price)
        product.stock = int(stock)
        product.category_id = int(category_id)

        # Image handling
        if image_file and image_file.filename:
            UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'products')
            filename = process_product_image(image_file, UPLOAD_FOLDER, size=(800, 800))
            if filename:
                product.image = url_for('static', filename=f'images/products/{filename}')
            else:
                flash('Ошибка при обработке изображения товара.', 'warning')

        db.session.commit()
        flash(f'Товар "{product.name}" успешно обновлен.', 'success')
        return redirect(url_for('admin.manage_products'))

    return render_template('admin/product_form.html', form_title='Редактировать товар', form_action=url_for('admin.edit_product', product_id=product.id), categories=categories, product=product)


@admin_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@permission_required('manage_products')
def delete_product(product_id):
    """Delete product."""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Товар "{product.name}" удален.', 'success')
    return redirect(url_for('admin.manage_products'))


@admin_bp.route('/reviews')
@permission_required('manage_reviews')
def admin_reviews():
    """Admin reviews management."""
    query = Review.query.order_by(Review.created_at.desc())
    
    search_term = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip() # 'approved', 'pending', 'all'
    
    if search_term:
        query = query.join(Product).filter(Product.name.ilike(f'%{search_term}%'))
        
    if status == 'approved':
        query = query.filter(Review.is_approved == True)
    elif status == 'pending':
        query = query.filter(Review.is_approved == False)
        
    reviews = query.all()
    
    return render_template('admin/reviews.html',
                           reviews=reviews,
                           search_term=search_term,
                           selected_status=status)


@admin_bp.route('/review/delete/<int:review_id>', methods=['POST'])
@admin_required
def delete_review(review_id):
    """Delete review."""
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удален.', 'success')
    return redirect(url_for('admin.admin_reviews'))


@admin_bp.route('/products')
@permission_required('manage_products')
def manage_products():
    """Manage products."""
    query = Product.query

    search_term = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    page = request.args.get('page', 1, type=int)

    if search_term:
        # Добавляем поиск по имени и описанию
        query = query.filter(db.or_(
            Product.name.ilike(f'%{search_term}%'),
            Product.description.ilike(f'%{search_term}%')
        ))

    if category_id:
        query = query.filter_by(category_id=category_id)

    products = query.paginate(page=page, per_page=12)
    categories = Category.query.all()

    return render_template('admin/products.html',
                           products=products,
                           categories=categories,
                           search_term=search_term,
                           selected_category_id=category_id)


@admin_bp.route('/promo-codes', methods=['GET', 'POST'])
@permission_required('manage_promo_codes')
def admin_promo_codes():
    promo_codes = PromoCode.query.all()
    return render_template('admin/promo_codes.html', promo_codes=promo_codes)


@admin_bp.route('/promo-code/add', methods=['GET', 'POST'])
@admin_required
def add_promo_code():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        discount_type = request.form.get('discount_type')
        discount_value = request.form.get('discount_value')
        is_active = request.form.get('is_active') == 'on'
        valid_from_str = request.form.get('valid_from')
        valid_until_str = request.form.get('valid_until')
        max_uses = request.form.get('max_uses', type=int)
        
        if not all([code, discount_type, discount_value]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('admin.add_promo_code'))
            
        # Check if code already exists
        if PromoCode.query.filter_by(code=code).first():
            flash(f'Промокод "{code}" уже существует.', 'error')
            return redirect(url_for('admin.add_promo_code'))
            
        try:
            discount_value = float(discount_value)
            max_uses = max_uses if max_uses is not None else -1
            valid_from = datetime.strptime(valid_from_str, '%Y-%m-%d') if valid_from_str else datetime.now(timezone.utc)
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d') if valid_until_str else None
            
            promo_code = PromoCode(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                is_active=is_active,
                valid_from=valid_from,
                valid_until=valid_until,
                max_uses=max_uses
            )
            db.session.add(promo_code)
            db.session.commit()
            flash(f'Промокод "{code}" успешно добавлен.', 'success')
            return redirect(url_for('admin.admin_promo_codes'))
        except ValueError:
            flash('Неверный формат данных.', 'error')
            return redirect(url_for('admin.add_promo_code'))
        
    return render_template('admin/promo_code_form.html', form_title='Добавить промокод', form_action=url_for('admin.add_promo_code'))


@admin_bp.route('/promo-code/edit/<int:promo_code_id>', methods=['GET', 'POST'])
@admin_required
def edit_promo_code(promo_code_id):
    """Edit existing promo code."""
    promo_code = PromoCode.query.get_or_404(promo_code_id)

    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        discount_type = request.form.get('discount_type')
        discount_value = request.form.get('discount_value')
        is_active = request.form.get('is_active') == 'on'
        valid_from_str = request.form.get('valid_from')
        valid_until_str = request.form.get('valid_until')
        max_uses = request.form.get('max_uses', type=int)
        
        if not all([code, discount_type, discount_value]):
            flash('Пожалуйста, заполните все обязательные поля.', 'error')
            return redirect(url_for('admin.edit_promo_code', promo_code_id=promo_code.id))
            
        # Check if code already exists for another promo code
        if PromoCode.query.filter(PromoCode.code == code, PromoCode.id != promo_code.id).first():
            flash(f'Промокод "{code}" уже существует.', 'error')
            return redirect(url_for('admin.edit_promo_code', promo_code_id=promo_code.id))
            
        try:
            discount_value = float(discount_value)
            max_uses = max_uses if max_uses is not None else -1
            valid_from = datetime.strptime(valid_from_str, '%Y-%m-%d') if valid_from_str else None
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d') if valid_until_str else None
            
            promo_code.code = code
            promo_code.discount_type = discount_type
            promo_code.discount_value = discount_value
            promo_code.is_active = is_active
            promo_code.valid_from = valid_from
            promo_code.valid_until = valid_until
            promo_code.max_uses = max_uses
            
            db.session.commit()
            flash(f'Промокод "{code}" успешно обновлен.', 'success')
            return redirect(url_for('admin.admin_promo_codes'))
        except ValueError:
            flash('Неверный формат данных.', 'error')
            return redirect(url_for('admin.edit_promo_code', promo_code_id=promo_code.id))
        
    return render_template('admin/promo_code_form.html', form_title='Редактировать промокод', form_action=url_for('admin.edit_promo_code', promo_code_id=promo_code.id), promo_code=promo_code)

@admin_bp.route('/promo-codes/delete/<int:promo_code_id>', methods=['POST'])
@admin_required
def delete_promo_code(promo_code_id):
    """Delete a promo code."""
    promo_code = PromoCode.query.get_or_404(promo_code_id)
    
    # Check if the promo code is used in any order (optional, but good practice)
    if Order.query.filter_by(promo_code_id=promo_code_id).first():
        flash('Невозможно удалить промокод, так как он использовался в заказах.', 'error')
        return redirect(url_for('admin.admin_promo_codes'))
        
    db.session.delete(promo_code)
    db.session.commit()
    flash(f'Промокод "{promo_code.code}" успешно удален.', 'success')
    
    return redirect(url_for('admin.admin_promo_codes'))


@admin_bp.route('/promo-codes/send', methods=['GET', 'POST'])
@permission_required('send_mass_emails')
def admin_send_promo_emails():
    """Send promo codes to all users."""
    if request.method == 'POST':
        promo_code_id = request.form.get('promo_code_id')
        subject = request.form.get('subject')
        body_template = request.form.get('body_template') # Now it's the template file path

        if not all([promo_code_id, subject, body_template]):
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('admin.admin_send_promo_emails'))

        promo_code = PromoCode.query.get(promo_code_id)
        if not promo_code:
            flash('Промокод не найден.', 'error')
            return redirect(url_for('admin.admin_send_promo_emails'))

        users = User.query.filter_by(is_verified=True).all()
        sent_count = 0
        for user in users:
            if send_mass_promo_code_email(user.email, subject, body_template, promo_code):
                sent_count += 1
                # Небольшая задержка, чтобы не перегружать почтовый сервер, если он реальный
                # time.sleep(0.1) # Закомментировано для быстрой работы в песочнице
                pass # The logic is moved above, this line is now redundant but kept for context.

        # Увеличиваем счетчик использования промокода, если он не безлимитный
        if promo_code.max_uses != -1:
            promo_code.current_uses += sent_count

        campaign = PromoCodeCampaign(
            promo_code_id=promo_code.id,
            sender_id=current_user.id,
            subject=subject,
            body_template=body_template,
            recipient_count=sent_count
        )
        db.session.add(campaign)
        db.session.commit()

        flash(f'Промокод "{promo_code.code}" отправлен {sent_count} пользователям.', 'success')
        return redirect(url_for('admin.admin_promo_codes'))

    promo_codes = PromoCode.query.filter_by(is_active=True).all()
    return render_template('admin/send_promo_form.html', promo_codes=promo_codes, promo_code=PromoCode())



@admin_bp.route('/categories')
@permission_required('manage_categories')
def admin_categories():
    """Admin categories management."""
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/category/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    """Add new category."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        image_file = request.files.get('image')
        
        if not name:
            flash('Пожалуйста, введите название категории.', 'error')
            return redirect(url_for('admin.add_category'))
            
        slug = slugify(name)
        
        category = Category(name=name, slug=slug)
        
        # Обработка изображения
        if image_file and image_file.filename:
            # Используем ту же логику, что и для товаров, но с другим размером
            UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'categories')
            # Размер для категорий (например, 300x300)
            filename = process_product_image(image_file, UPLOAD_FOLDER, size=(300, 300))
            if filename:
                category.image = url_for('static', filename=f'images/categories/{filename}')
            else:
                flash('Ошибка при обработке изображения категории.', 'warning')
        
        db.session.add(category)
        db.session.commit()
        flash(f'Категория "{name}" успешно добавлена.', 'success')
        return redirect(url_for('admin.admin_categories'))
        
    return render_template('admin/category_form.html', form_title='Добавить категорию', form_action=url_for('admin.add_category'))


@admin_bp.route('/category/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit existing category."""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name', '').strip()
        image_file = request.files.get('image')
        delete_image = request.form.get('delete_image')
        
        category.slug = slugify(category.name)
        
        if not category.name:
            flash('Пожалуйста, введите название категории.', 'error')
            return redirect(url_for('admin.edit_category', category_id=category.id))
            
        # Обработка удаления изображения
        if delete_image == 'on' and category.image:
            # Удаляем старый файл
            try:
                old_path = os.path.join(os.path.dirname(__file__), category.image.lstrip('/'))
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception as e:
                print(f"Ошибка при удалении старого изображения категории: {e}")
            category.image = None
            
        # Обработка загрузки нового изображения
        if image_file and image_file.filename:
            UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'categories')
            # Удаляем старый файл, если он есть
            if category.image:
                try:
                    old_path = os.path.join(os.path.dirname(__file__), category.image.lstrip('/'))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"Ошибка при удалении старого изображения категории: {e}")
            
            # Сохраняем новый файл
            filename = process_product_image(image_file, UPLOAD_FOLDER, size=(300, 300))
            if filename:
                category.image = url_for('static', filename=f'images/categories/{filename}')
            else:
                flash('Ошибка при обработке изображения категории.', 'warning')
            
        db.session.commit()
        flash(f'Категория "{category.name}" успешно обновлена.', 'success')
        return redirect(url_for('admin.admin_categories'))
        
    return render_template('admin/category_form.html', form_title='Редактировать категорию', form_action=url_for('admin.edit_category', category_id=category.id), category=category)


@admin_bp.route('/category/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    """Delete a category."""
    category = Category.query.get_or_404(category_id)

    # Check if any products are linked to this category
    if Product.query.filter_by(category_id=category_id).first():
        flash('Невозможно удалить категорию, так как к ней привязаны товары.', 'error')
        return redirect(url_for('admin.admin_categories'))

    db.session.delete(category)
    db.session.commit()
    flash(f'Категория "{category.name}" успешно удалена.', 'success')

    return redirect(url_for('admin.admin_categories'))


# ============================================================================
# SUBSCRIBERS MANAGEMENT
# ============================================================================

@admin_bp.route('/subscribers')
@permission_required('manage_users')
def admin_subscribers():
    """Admin subscribers management."""
    subscribers = Subscriber.query.order_by(Subscriber.subscribed_at.desc()).all()
    return render_template('admin/subscribers.html', subscribers=subscribers)


@admin_bp.route('/subscriber/delete/<int:subscriber_id>', methods=['POST'])
@permission_required('manage_users')
def delete_subscriber(subscriber_id):
    """Delete a subscriber."""
    subscriber = Subscriber.query.get_or_404(subscriber_id)

    db.session.delete(subscriber)
    db.session.commit()
    flash(f'Подписчик "{subscriber.email}" удален.', 'success')

    return redirect(url_for('admin.admin_subscribers'))


@admin_bp.route('/subscribers/send-promo', methods=['GET', 'POST'])
@permission_required('send_mass_emails')
def admin_send_subscriber_promo():
    """Send promo codes to verified subscribers."""
    if request.method == 'POST':
        promo_code_id = request.form.get('promo_code_id')
        subject = request.form.get('subject')
        body_template = request.form.get('body_template')

        if not all([promo_code_id, subject, body_template]):
            flash('Пожалуйста, заполните все поля.', 'error')
            return redirect(url_for('admin.admin_send_subscriber_promo'))

        promo_code = PromoCode.query.get(promo_code_id)
        if not promo_code:
            flash('Промокод не найден.', 'error')
            return redirect(url_for('admin.admin_send_subscriber_promo'))

        # Get verified subscribers
        subscribers = Subscriber.query.filter_by(is_verified=True, is_active=True).all()
        sent_count = 0
        for subscriber in subscribers:
            if send_mass_promo_code_email(subscriber.email, subject, body_template, promo_code):
                sent_count += 1

        # Update promo code usage
        if promo_code.max_uses != -1:
            promo_code.current_uses += sent_count

        campaign = PromoCodeCampaign(
            promo_code_id=promo_code.id,
            sender_id=current_user.id,
            subject=subject,
            body_template=body_template,
            recipient_count=sent_count
        )
        db.session.add(campaign)
        db.session.commit()

        flash(f'Промокод "{promo_code.code}" отправлен {sent_count} подписчикам.', 'success')
        return redirect(url_for('admin.admin_subscribers'))

    promo_codes = PromoCode.query.filter_by(is_active=True).all()
    return render_template('admin/send_subscriber_promo.html', promo_codes=promo_codes, promo_code=PromoCode())


@main_bp.route('/verify-subscription')
def verify_subscription():
    """Verify newsletter subscription (legacy route, now auto-verified)."""
    flash('Подписка уже подтверждена автоматически.', 'info')
    return redirect(url_for('main.index'))


# ============================================================================
# NEWSLETTER SUBSCRIPTION
# ============================================================================

@main_bp.route('/subscribe', methods=['POST'], endpoint='subscribe')
def handle_subscription():
    """Мгновенная подписка на рассылку с отправкой приветственного промокода WELCOME30"""
    email = request.form.get('email', '').strip()

    if not email:
        flash('Пожалуйста, введите email.', 'error')
        return redirect(url_for('main.index'))

    # Проверяем, не подписан ли уже
    existing_subscriber = Subscriber.query.filter_by(email=email).first()
    if existing_subscriber and existing_subscriber.is_verified:
        flash('Вы уже подписаны на рассылку.', 'info')
        return redirect(url_for('main.index'))

    # Создаём или обновляем подписчика (автоматически верифицируем)
    if existing_subscriber:
        # Обновляем существующего подписчика
        existing_subscriber.is_verified = True
        existing_subscriber.verified_at = datetime.now(timezone.utc)
        existing_subscriber.verification_token = None
        existing_subscriber.verification_token_expires = None
        db.session.commit()
        subscriber = existing_subscriber
    else:
        # Создаём нового подписчика
        subscriber = Subscriber(
            email=email,
            is_active=True,
            is_verified=True,
            verified_at=datetime.now(timezone.utc)
        )
        db.session.add(subscriber)
        db.session.commit()

    # Генерируем приветственный промокод WELCOME30 (30% скидка)
    promo_code_str = "WELCOME30"
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    # Проверяем, существует ли уже такой промокод
    existing_promo = PromoCode.query.filter_by(code=promo_code_str).first()
    if not existing_promo:
        promo_code = PromoCode(
            code=promo_code_str,
            discount_type='percent',
            discount_value=30.0,
            max_uses=1,  # Только для одного использования
            valid_until=expires_at,
            is_active=True
        )
        db.session.add(promo_code)
        db.session.commit()
    else:
        promo_code = existing_promo

    # Отправляем приветственное письмо с промокодом
    if send_promo_code_email(email, promo_code_str):
        flash('Поздравляем! Вы подписались на рассылку. Проверьте почту - там промокод WELCOME30 на 30% скидку!', 'success')
    else:
        flash('Вы подписались на рассылку! Промокод WELCOME30 сохранён, но письмо не удалось отправить.', 'warning')

    return redirect(url_for('main.index'))
