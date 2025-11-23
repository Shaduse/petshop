"""
Populate database with test breeds and products for breed detection feature.
"""

from app import create_app
from app.models import db, Product, Category, Breed, product_breeds, Role
from datetime import datetime, timezone
from slugify import slugify
import random

app = create_app()

# Sample data for roles
ROLES_DATA = [
    {'name': 'Admin', 'description': 'Полный доступ ко всем функциям', 'permissions': ['manage_users', 'manage_products', 'manage_orders', 'manage_promo_codes', 'manage_categories', 'manage_reviews', 'send_mass_emails']},
    {'name': 'Manager', 'description': 'Управление товарами, заказами, категориями, отзывами и рассылками', 'permissions': ['manage_products', 'manage_orders', 'manage_categories', 'manage_reviews', 'send_mass_emails']},
    {'name': 'Moderator', 'description': 'Управление отзывами и массовыми рассылками', 'permissions': ['manage_reviews', 'send_mass_emails']},
]

# Sample data for breeds
BREEDS_DATA = [
    # Dogs
    {'name': 'Лабрадор-ретривер', 'pet_type': 'собака', 'description': 'Дружелюбная и активная порода, отличный компаньон.'},
    {'name': 'Немецкая овчарка', 'pet_type': 'собака', 'description': 'Умная, преданная и легко обучаемая служебная собака.'},
    {'name': 'Йоркширский терьер', 'pet_type': 'собака', 'description': 'Маленькая, энергичная и смелая декоративная порода.'},
    {'name': 'Сибирский хаски', 'pet_type': 'собака', 'description': 'Ездовая собака, требующая много физической активности.'},
    
    # Cats
    {'name': 'Мейн-кун', 'pet_type': 'кошка', 'description': 'Крупная, ласковая и общительная порода кошек.'},
    {'name': 'Британская короткошерстная', 'pet_type': 'кошка', 'description': 'Спокойная, плюшевая кошка с независимым характером.'},
    {'name': 'Сфинкс', 'pet_type': 'кошка', 'description': 'Бесшерстная, очень ласковая и требующая особого ухода порода.'},
    {'name': 'Шотландская вислоухая', 'pet_type': 'кошка', 'description': 'Кошка с уникальными загнутыми ушами, очень спокойная.'},
]

# Sample data for products
PRODUCTS_DATA = [
    # Dog Food (Labrador, German Shepherd)
    {'name': 'Корм для крупных собак "Актив"', 'description': 'Высокобелковый корм для активных собак крупных пород.', 'price': 2500, 'category_slug': 'dog-food', 'breeds': ['Лабрадор-ретривер', 'Немецкая овчарка']},
    {'name': 'Корм для щенков "Рост"', 'description': 'Сбалансированный корм для щенков всех пород.', 'price': 1800, 'category_slug': 'dog-food', 'breeds': ['Лабрадор-ретривер', 'Немецкая овчарка', 'Йоркширский терьер', 'Сибирский хаски']},
    {'name': 'Корм для мелких пород "Мини"', 'description': 'Специализированный корм для собак мелких пород.', 'price': 1500, 'category_slug': 'dog-food', 'breeds': ['Йоркширский терьер']},
    
    # Cat Food (Maine Coon, Sphynx)
    {'name': 'Корм для длинношерстных кошек', 'description': 'Помогает предотвратить образование комков шерсти.', 'price': 1600, 'category_slug': 'cat-food', 'breeds': ['Мейн-кун', 'Британская короткошерстная']},
    {'name': 'Корм для чувствительной кожи', 'description': 'Гипоаллергенный корм для кошек с чувствительной кожей.', 'price': 1900, 'category_slug': 'cat-food', 'breeds': ['Сфинкс']},
    
    # Toys (Husky, Yorkie, Scottish Fold)
    {'name': 'Прочная канатная игрушка', 'description': 'Идеально подходит для перетягивания и жевания.', 'price': 500, 'category_slug': 'toys', 'breeds': ['Сибирский хаски', 'Немецкая овчарка']},
    {'name': 'Мягкая мышка с кошачьей мятой', 'description': 'Любимая игрушка для кошек.', 'price': 250, 'category_slug': 'toys', 'breeds': ['Мейн-кун', 'Шотландская вислоухая']},
    {'name': 'Интерактивная игрушка-головоломка', 'description': 'Развивает интеллект и занимает питомца.', 'price': 1200, 'category_slug': 'toys', 'breeds': ['Лабрадор-ретривер', 'Британская короткошерстная']},
    
    # Accessories (All)
    {'name': 'Универсальный поводок 3м', 'description': 'Прочный нейлоновый поводок для прогулок.', 'price': 700, 'category_slug': 'accessories', 'breeds': []},
    {'name': 'Миска для медленного кормления', 'description': 'Помогает собакам есть медленнее для лучшего пищеварения.', 'price': 900, 'category_slug': 'accessories', 'breeds': ['Лабрадор-ретривер']},
    
    # Grooming (Sphynx, Maine Coon)
    {'name': 'Специальный шампунь для бесшерстных кошек', 'description': 'Бережный уход за кожей сфинксов.', 'price': 850, 'category_slug': 'grooming', 'breeds': ['Сфинкс']},
    {'name': 'Щетка для вычесывания подшерстка', 'description': 'Идеально подходит для длинношерстных пород.', 'price': 1100, 'category_slug': 'grooming', 'breeds': ['Мейн-кун', 'Сибирский хаски']},
    
    # Beds (German Shepherd, British Shorthair)
    {'name': 'Ортопедический лежак XL', 'description': 'Большой лежак для крупных собак с проблемами суставов.', 'price': 4500, 'category_slug': 'beds', 'breeds': ['Немецкая овчарка']},
    {'name': 'Мягкий домик-будка', 'description': 'Уютное место для сна и отдыха кошек.', 'price': 2200, 'category_slug': 'beds', 'breeds': ['Британская короткошерстная', 'Шотландская вислоухая']},
]

def populate_roles():
    """Add sample roles to the database."""
    print("--- Populating Roles ---")
    for data in ROLES_DATA:
        if not Role.query.filter_by(name=data['name']).first():
            role = Role(
                name=data['name'],
                description=data['description']
            )
            role.set_permissions(data['permissions'])
            db.session.add(role)
            print(f"✓ Added role: {data['name']}")
    db.session.commit()

def populate_breeds():
    """Add sample breeds to the database."""
    print("--- Populating Breeds ---")
    for data in BREEDS_DATA:
        slug = slugify(data['name'])
        if not Breed.query.filter_by(slug=slug).first():
            breed = Breed(
                name=data['name'],
                slug=slug,
                pet_type=data['pet_type'],
                description=data['description']
            )
            db.session.add(breed)
            print(f"✓ Added breed: {data['name']}")
    db.session.commit()

def populate_products():
    """Add sample products and link them to breeds."""
    print("\n--- Populating Products ---")
    
    # Get all categories and breeds for linking
    categories = {c.slug: c for c in Category.query.all()}
    breeds = {b.name: b for b in Breed.query.all()}
    
    for i, data in enumerate(PRODUCTS_DATA):
        slug = slugify(data['name'] + '-' + str(i))
        if not Product.query.filter_by(slug=slug).first():
            category = categories.get(data['category_slug'])
            if not category:
                print(f"✗ Category not found for product: {data['name']}")
                continue
                
            product = Product(
                name=data['name'],
                slug=slug,
                description=data['description'],
                price=data['price'],
                category_id=category.id,
                stock=random.randint(10, 50),
                image=f'/static/img/product_{i+1}.jpg' # Placeholder image
            )
            
            # Link breeds
            for breed_name in data['breeds']:
                breed = breeds.get(breed_name)
                if breed:
                    product.breeds.append(breed)
            
            db.session.add(product)
            print(f"✓ Added product: {data['name']}")
            
    db.session.commit()

def main():
    """Main function to run population scripts."""
    with app.app_context():
        populate_roles()
        populate_breeds()
        populate_products()
        print("\n✓ Database population complete!")

if __name__ == '__main__':
    main()
