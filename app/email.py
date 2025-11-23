"""
Email sending utilities.
"""

from flask import render_template
from flask_mail import Message
from app import mail
import random
import string
from datetime import datetime


def send_verification_email(user_email, code):
    """Send verification code to email."""
    try:
        msg = Message(
            subject='Код подтверждения PetShop',
            recipients=[user_email],
            html=f'''
            <h2>Добро пожаловать в PetShop!</h2>
            <p>Ваш код подтверждения:</p>
            <h1 style="color: #512da8; font-size: 32px; letter-spacing: 5px;">{code}</h1>
            <p>Код действителен 15 минут.</p>
            <p>Если вы не регистрировались, проигнорируйте это письмо.</p>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_password_reset_email(user_email, code):
    """Send password reset code to email."""
    try:
        msg = Message(
            subject='Восстановление пароля PetShop',
            recipients=[user_email],
            html=f'''
            <h2>Восстановление пароля</h2>
            <p>Ваш код подтверждения для смены пароля:</p>
            <h1 style="color: #512da8; font-size: 32px; letter-spacing: 5px;">{code}</h1>
            <p>Код действителен 15 минут.</p>
            <p>Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.</p>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def generate_verification_code():
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


def send_order_confirmation_email(order):
    """Send order confirmation email."""
    try:
        msg = Message(
            subject=f'Ваш заказ №{order.order_number} подтвержден!',
            recipients=[order.user.email],
            html=f'''
            <h2>Заказ №{order.order_number} успешно оформлен!</h2>
            <p>Спасибо за ваш заказ в PetShop. Мы немедленно приступим к его обработке.</p>
            
            <h3>Детали заказа:</h3>
            <p><strong>Дата заказа:</strong> {order.created_at.strftime('%d.%m.%Y %H:%M')}</p>
            <p><strong>Общая сумма:</strong> {order.total:.2f} ₽</p>
            <p><strong>Статус:</strong> {order.status.value.capitalize()}</p>
            
            <h4>Состав заказа:</h4>
            <ul>
                {''.join([f'<li>{item.product.name} ({item.quantity} шт.) - {item.price:.2f} ₽/шт.</li>' for item in order.items])}
            </ul>
            
            <p>Мы свяжемся с вами, как только статус заказа изменится.</p>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending order confirmation email: {e}")
        return False

from flask import render_template
from flask import render_template
from flask_mail import Message
from app import mail
import random
import string
from datetime import datetime


def send_mass_promo_code_email(user_email, subject, body_template, promo_code):
    """Send a mass promo code email with custom subject and body using Jinja2 template."""
    try:
        # The body_template is now the name of the template file (e.g., 'emails/promo_mass.html')
        # We pass the promo_code object to the template for rendering
        html_body = render_template(
            body_template,
            promo_code=promo_code,
            user_email=user_email, # Can be used for unsubscribe link or personalization
            now=datetime.now # Pass datetime.now for use in the base template footer
        )
        
        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending mass promo code email to {user_email}: {e}")
        return False

def send_subscription_verification_email(user_email, verification_code):
    """Send subscription verification email."""
    try:
        verification_url = f"http://127.0.0.1:5000/verify-subscription?token={verification_code}"
        msg = Message(
            subject='Подтверждение подписки на рассылку PetShop',
            recipients=[user_email],
            html=f'''
            <h2>Подтверждение подписки</h2>
            <p>Спасибо, что подписались на нашу рассылку! Для завершения подписки нажмите на ссылку ниже:</p>
            <p><a href="{verification_url}" style="background: #512da8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Подтвердить подписку</a></p>
            <p>Или скопируйте эту ссылку в браузер: {verification_url}</p>
            <p>Ссылка действительна 24 часа.</p>
            <p>Если вы не подписывались на рассылку, просто проигнорируйте это письмо.</p>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending subscription verification email: {e}")
        return False


def send_promo_code_email(user_email, promo_code):
    """Send a welcome promo code to a new subscriber."""
    try:
        # Определяем процент скидки на основе кода
        if promo_code == "WELCOME30":
            discount_percent = 30
            discount_text = "30% скидку"
        else:
            discount_percent = 10  # По умолчанию для других промокодов
            discount_text = "скидку"

        msg = Message(
            subject='Добро пожаловать в PetShop! Ваш приветственный промокод',
            recipients=[user_email],
            html=f'''
            <h2>🎉 Добро пожаловать в семью PetShop!</h2>
            <p>Спасибо, что подписались на нашу рассылку! В качестве приветственного подарка мы дарим вам специальный промокод на <strong>{discount_text}</strong> на ваш следующий заказ:</p>
            <div style="text-align: center; margin: 30px 0;">
                <h1 style="color: #512da8; font-size: 36px; letter-spacing: 8px; background: #f8f9fa; padding: 20px; border-radius: 10px; display: inline-block;">{promo_code}</h1>
            </div>
            <p><strong>Как использовать промокод:</strong></p>
            <ul>
                <li>Скопируйте код: <code style="background: #e9ecef; padding: 2px 6px; border-radius: 3px;">{promo_code}</code></li>
                <li>Добавьте товары в корзину на нашем сайте</li>
                <li>Вставьте промокод при оформлении заказа</li>
                <li>Наслаждайтесь скидкой!</li>
            </ul>
            <p>⏰ <strong>Срок действия:</strong> 30 дней с момента получения</p>
            <p>🐾 <strong>Ждем вас за покупками!</strong></p>
            <p style="color: #6c757d; font-size: 14px;">Если у вас возникнут вопросы, пишите нам на support@petshop.com</p>
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending promo code email: {e}")
        return False
