import os
from PIL import Image
from werkzeug.utils import secure_filename
import secrets

def process_product_image(image_file, upload_folder, size=(800, 800), format='webp'):
    """
    Обрабатывает загруженное изображение товара:
    1. Генерирует уникальное имя файла.
    2. Изменяет размер и обрезает изображение до заданного размера (квадрат).
    3. Конвертирует изображение в заданный формат (WebP).
    4. Сохраняет файл в папку загрузки.

    :param image_file: Объект FileStorage из request.files.
    :param upload_folder: Абсолютный путь к папке для сохранения.
    :param size: Кортеж (ширина, высота) для изменения размера.
    :param format: Формат для сохранения (например, 'webp', 'jpeg', 'png').
    :return: Относительный путь к сохраненному файлу или None.
    """
    if not image_file or not image_file.filename:
        return None

    # 1. Генерируем уникальное имя файла
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(image_file.filename)
    
    # Используем secure_filename для очистки имени, но расширение меняем на целевой формат
    filename = secure_filename(random_hex + '.' + format)
    
    # Создаем полный путь для сохранения
    full_path = os.path.join(upload_folder, filename)

    # 2. Открываем изображение с помощью Pillow
    try:
        img = Image.open(image_file)
    except Exception as e:
        print(f"Ошибка при открытии изображения: {e}")
        return None

    # 3. Изменяем размер и обрезаем (crop)
    # 3. Изменяем размер и обрезаем (crop) до квадрата
    width, height = img.size
    target_size = size[0] # Предполагаем, что size - это квадрат (800, 800)
    
    # Определяем, какую сторону обрезать, чтобы получить квадрат
    if width > height:
        # Обрезаем по ширине
        left = (width - height) / 2
        right = (width + height) / 2
        top = 0
        bottom = height
        img = img.crop((left, top, right, bottom))
    elif height > width:
        # Обрезаем по высоте
        left = 0
        right = width
        top = (height - width) / 2
        bottom = (height + width) / 2
        img = img.crop((left, top, right, bottom))
        
    # Изменяем размер до целевого (например, 800x800)
    img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    # 4. Сохраняем в заданном формате
    try:
        # Убедимся, что папка существует
        os.makedirs(upload_folder, exist_ok=True)
        
        # Сохраняем. Для WebP можно указать качество.
        if format.lower() == 'webp':
            img.save(full_path, format='WEBP', quality=85)
        else:
            img.save(full_path, format=format.upper())
            
        # Возвращаем имя файла, которое будет сохранено в БД
        return filename
        
    except Exception as e:
        print(f"Ошибка при сохранении изображения: {e}")
        return None

if __name__ == '__main__':
    # Пример использования (для тестирования)
    # from flask import Flask
    # app = Flask(__name__)
    # app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'app', 'static', 'images', 'products')
    # # Создайте фиктивный объект FileStorage для тестирования
    # # from werkzeug.datastructures import FileStorage
    # # with open('test_image.jpg', 'rb') as fp:
    # #     file_storage = FileStorage(fp, filename='test_image.jpg')
    # #     filename = process_product_image(file_storage, app.config['UPLOAD_FOLDER'])
    # #     print(f"Сохраненный файл: {filename}")
    pass
