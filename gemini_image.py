import os
import requests
from io import BytesIO
from PIL import Image
from openai import OpenAI

def generate_image(prompt: str, output_path: str = "generated_image.png") -> str:
    """Генерирует изображение через прокси RiftAI (OpenAI-совместимый эндпоинт)."""
    
    # Подтягиваем переменные из окружения хостинга Bothost
    api_key = os.getenv("RIFT_API_KEY")
    base_url = os.getenv("RIFT_BASE_URL", "https://riftai.su/v1")

    if not api_key:
        raise ValueError("Ошибка: Переменная окружения RIFT_API_KEY не задана на хостинге Bothost.")

    # Инициализируем клиент OpenAI с кастомным адресом (RiftAI)
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # Запрашиваем генерацию. 
    # ВАЖНО: В параметре model указываем именно "gemini-2.5-flash-image"
    response = client.images.generate(
        model="gemini-2.5-flash-image",
        prompt=prompt,
        n=1,
        size="1024x1024" # Стандартный размер для генерации
    )

    # Большинство OpenAI-совместимых прокси возвращают URL готовой картинки
    image_url = response.data[0].url
    if not image_url:
        raise ValueError("Резервный адрес изображения не получен от API.")

    # Скачиваем сгенерированную картинку по ссылке и сохраняем её на диск
    img_data = requests.get(image_url).content
    image = Image.open(BytesIO(img_data))
    image.save(output_path)
    
    return output_path
