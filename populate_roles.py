"""
Populate database with default roles.
"""

from app import create_app
from app.models import db, Role

app = create_app()

ROLES_DATA = [
    {'name': 'Admin', 'description': 'Полный доступ ко всем функциям', 'permissions': ['manage_users', 'manage_products', 'manage_orders', 'manage_promo_codes', 'manage_categories', 'manage_reviews', 'send_mass_emails']},
    {'name': 'Manager', 'description': 'Управление товарами, заказами, категориями, отзывами, промокодами и рассылками', 'permissions': ['manage_products', 'manage_orders', 'manage_categories', 'manage_reviews', 'manage_promo_codes', 'send_mass_emails']},
    {'name': 'Moderator', 'description': 'Управление отзывами и массовыми рассылками', 'permissions': ['manage_reviews', 'send_mass_emails']},
]

def populate_roles():
    """Add sample roles to the database."""
    print("--- Populating Roles ---")
    for data in ROLES_DATA:
        role = Role.query.filter_by(name=data['name']).first()
        if not role:
            role = Role(
                name=data['name'],
                description=data['description']
            )
            db.session.add(role)
            print(f"Added role: {data['name']}")
        role.set_permissions(data['permissions'])
        print(f"Updated permissions for role: {data['name']}")
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        populate_roles()
        print("\n✓ Roles population complete!")