"""
Initialize database with admin user and sample data.
"""

from app import create_app
from app.models import db, User, Category, Product, Role, PromoCode
from datetime import datetime, timezone

app = create_app()

with app.app_context():
    db.create_all()
    
    # Create default roles
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(name='Admin', description='Administrator with full access')
        admin_role.set_permissions(['manage_users', 'manage_products', 'manage_orders', 'manage_promo_codes', 'manage_categories', 'manage_reviews', 'send_mass_emails'])
        db.session.add(admin_role)

    manager_role = Role.query.filter_by(name='Manager').first()
    if not manager_role:
        manager_role = Role(name='Manager', description='Manager with access to products, orders, categories, reviews, promo codes, and emails')
        db.session.add(manager_role)
    manager_role.set_permissions(['manage_products', 'manage_orders', 'manage_categories', 'manage_reviews', 'manage_promo_codes', 'send_mass_emails'])

    user_role = Role.query.filter_by(name='User').first()
    if not user_role:
        user_role = Role(name='User', description='Standard registered user')
        db.session.add(user_role)
        
    db.session.commit() # Commit roles first
    
    # Check if admin exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@petshop.com',
            first_name='Admin',
            last_name='User',
            is_verified=True,
            privacy_accepted=True,
            privacy_accepted_at=datetime.now(timezone.utc)
        )
        admin.set_password('admin123')
        admin.roles.append(admin_role)
        db.session.add(admin)
        print("Admin user created (username: admin, password: admin123)")
    
    # Create categories if not exist
    categories_data = [
        {'name': 'Корма для собак', 'slug': 'dog-food', 'description': 'Качественные корма для собак всех возрастов'},
        {'name': 'Корма для кошек', 'slug': 'cat-food', 'description': 'Питательные корма для кошек'},
        {'name': 'Игрушки', 'slug': 'toys', 'description': 'Развлекательные игрушки для питомцев'},
        {'name': 'Аксессуары', 'slug': 'accessories', 'description': 'Ошейники, поводки и другие аксессуары'},
        {'name': 'Уход', 'slug': 'grooming', 'description': 'Средства для ухода за шерстью и здоровьем'},
        {'name': 'Лежаки и домики', 'slug': 'beds', 'description': 'Удобные лежаки и домики для питомцев'},
    ]
    
    for cat_data in categories_data:
        if not Category.query.filter_by(name=cat_data['name']).first():
            category = Category(**cat_data)
            db.session.add(category)
            print(f"Category created: {cat_data['name']}")
    
    db.session.commit()
    
    # Ensure existing users have the 'User' role if they don't have any
    # Ensure existing users have the 'User' role if they don't have any
    for user in User.query.all():
        if not user.roles:
            user.roles.append(user_role)
            
    # Sample products are now added via populate_db.py
    # import populate_db
    # populate_db.main() # This would require a change in how populate_db is run. We will keep it separate for simplicity.
    print("\n✓ Database initialized successfully!")
    print("\nAdmin credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("  Email: admin@petshop.com")

