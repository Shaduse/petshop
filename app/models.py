'''
Database models with normalized schema.
'''

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import enum

db = SQLAlchemy()


# ============================================================================
# ENUMS
# ============================================================================

class OrderStatus(enum.Enum):
    "Order status enumeration."
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


# ============================================================================
# USERS TABLE
# ============================================================================

# Association table for User-Role many-to-many relationship
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class Role(db.Model):
    "User role model."
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    # Permissions stored as a JSON string or integer bitmask. Using JSON for flexibility.
    permissions = db.Column(db.Text, default='[]') 
    
    def get_permissions(self):
        """Returns a list of permissions."""
        import json
        try:
            return json.loads(self.permissions)
        except:
            return []

    def set_permissions(self, perm_list):
        """Sets permissions from a list."""
        import json
        self.permissions = json.dumps(perm_list)

    def has_permission(self, permission_name):
        """Checks if the role has a specific permission."""
        return permission_name in self.get_permissions()
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    "User model with authentication."
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    
    # Account status
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    verification_token_expires = db.Column(db.DateTime)
    
    # Privacy & consent
    privacy_accepted = db.Column(db.Boolean, default=False)
    privacy_accepted_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_signed_in = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, lazy='select',
        backref=db.backref('users', lazy='dynamic'))
    addresses = db.relationship('Address', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        "Hash and set password."
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        "Check password hash."
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        "Check if the user is an admin (has 'Admin' role)."
        return any(role.name == 'Admin' for role in self.roles)

    def has_role(self, role_name):
        "Check if the user has a specific role."
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name):
        "Check if the user has a specific permission through any of their roles."
        # Admin always has all permissions
        if self.is_admin():
            return True
        
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'


# ============================================================================
# CATEGORIES TABLE
# ============================================================================

class Category(db.Model):
    "Product category model."
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    is_popular = db.Column(db.Boolean, default=False) # New column for Popular Categories
    
    # Display order
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'


# ============================================================================
# BREEDS TABLE
# ============================================================================

class Breed(db.Model):
    "Pet breed model for product recommendations."
    __tablename__ = 'breeds'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    pet_type = db.Column(db.String(50), nullable=False) # e.g., 'dog', 'cat'
    description = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', secondary='product_breeds', back_populates='breeds')

    def __repr__(self):
        return f'<Breed {self.name}>'

# Association table for many-to-many relationship between Product and Breed
product_breeds = db.Table('product_breeds',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('breed_id', db.Integer, db.ForeignKey('breeds.id'), primary_key=True)
)

# ============================================================================
# PRODUCTS TABLE
# ============================================================================

class Product(db.Model):
    "Product model."
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Category
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    
    # Relationships
    breeds = db.relationship('Breed', secondary=product_breeds, back_populates='products')
    
    # Pricing
    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float)  # For discounts
    
    # Inventory
    stock = db.Column(db.Integer, default=0)
    sku = db.Column(db.String(50), unique=True)
    
    # Media
    image = db.Column(db.String(255))
    
    # Display
    badge = db.Column(db.String(50))  # e.g., "NEW", "SALE", "HOT"
    is_featured = db.Column(db.Boolean, default=False)
    is_recommended = db.Column(db.Boolean, default=False) # New column for Recommended Products
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def average_rating(self):
        "Calculate the average rating for the product."
        reviews = [review for review in self.reviews if review.is_approved]
        if not reviews:
            return 0.0
        total_rating = sum(review.rating for review in reviews)
        return round(total_rating / len(reviews), 1)

    def __repr__(self):
        return f'<Product {self.name}>'


# ============================================================================
# CART TABLE
# ============================================================================

class CartItem(db.Model):
    "Shopping cart item model."
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)
    
    def __repr__(self):
        return f'<CartItem user_id={self.user_id} product_id={self.product_id}>'


# ============================================================================
# FAVORITES TABLE
# ============================================================================

class Favorite(db.Model):
    "User favorites model."
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_favorite'),)
    
    def __repr__(self):
        return f'<Favorite user_id={self.user_id} product_id={self.product_id}>'


# ============================================================================
# ADDRESSES TABLE
# ============================================================================

class Address(db.Model):
    "User address model."
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    street = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='Russia')
    is_default = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    orders = db.relationship('Order', backref='address', lazy='dynamic')
    
    def __repr__(self):
        return f'<Address {self.city}>'


# ============================================================================
# ORDERS TABLE
# ============================================================================

class Order(db.Model):
    "Order model."
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=False, index=True)
    
    # Order details
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # Promo code
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'), nullable=True)
    promo_code_rel = db.relationship('PromoCode', backref='orders')
    discount_amount = db.Column(db.Float, default=0.0)

    # Pricing
    subtotal = db.Column(db.Float, nullable=False)
    shipping_cost = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'


# ============================================================================
# ORDER ITEMS TABLE
# ============================================================================

class OrderItem(db.Model):
    "Order item model (line items in order)."
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    
    # Item details (snapshot of product at purchase time)
    product_name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False) # Price at time of order
    quantity = db.Column(db.Integer, nullable=False)
    
    # Calculated
    subtotal = db.Column(db.Float, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def image(self):
        "Возвращает путь к изображению продукта."
        return self.product.image if self.product else None
        
    def __repr__(self):
        return f'<OrderItem order_id={self.order_id} product_id={self.product_id}>'


# ============================================================================
# REVIEWS TABLE
# ============================================================================

class Review(db.Model):
    "Product review model."
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Review content
    rating = db.Column(db.Float, nullable=False)  # 1.0-5.0
    title = db.Column(db.String(150))
    content = db.Column(db.Text)
    
    # Moderation
    is_verified_purchase = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('product_id', 'user_id', name='unique_product_user_review'),)
    
    def __repr__(self):
        return f'<Review product_id={self.product_id} user_id={self.user_id}>'


# ============================================================================
# NEWSLETTER SUBSCRIBERS TABLE
# ============================================================================

class Subscriber(db.Model):
    "Newsletter subscriber model."
    __tablename__ = 'subscribers'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    verification_token_expires = db.Column(db.DateTime)

    # Timestamps
    subscribed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    verified_at = db.Column(db.DateTime)
    unsubscribed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Subscriber {self.email}>'

# ============================================================================
# PROMO CODE CAMPAIGN TABLE
# ============================================================================
class PromoCodeCampaign(db.Model):
    "Model to track mass promo code email campaigns."
    __tablename__ = 'promo_code_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True) # User who initiated the send
    subject = db.Column(db.String(255), nullable=False)
    body_template = db.Column(db.Text, nullable=False) # Template for the email body
    recipient_count = db.Column(db.Integer, default=0)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    promo_code = db.relationship('PromoCode', backref='campaigns')
    sender = db.relationship('User', backref='sent_campaigns')
    
    def __repr__(self):
        return f'<PromoCodeCampaign {self.subject} for {self.promo_code.code}>'

# ============================================================================
# PROMO CODES TABLE
# ============================================================================
class PromoCode(db.Model):
    "Promo code model."
    __tablename__ = 'promo_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    discount_type = db.Column(db.Enum('percent', 'fixed', name='discount_type'), nullable=False) # percent or fixed
    discount_value = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    valid_from = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    valid_until = db.Column(db.DateTime)
    max_uses = db.Column(db.Integer, default=-1) # -1 for unlimited
    current_uses = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<PromoCode {self.code} ({self.discount_value})>'
