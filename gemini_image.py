import os
import requests
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI

def generate_image(prompt: str, output_path: str = "generated_image.png") -> str:
    """Генерирует изображение через RiftAI."""

    api_key = os.getenv("RIFT_API_KEY")
    base_url = os.getenv("RIFT_BASE_URL", "https://riftai.su/v1")  # <-- обязательно /v1

    if not api_key:
        raise ValueError("RIFT_API_KEY не задан в переменных окружения")

    style = "character from Naruto anime, full body shot, anime style, gouache painting, rich paint strokes, vibrant colors, artistic canvas art, well proportioned anatomy, masterpiece, high quality"
    negative = "giant head, big head, disproportionate body, close-up, cropped, portrait, avoiding 3d render, photorealism, real life photo, blurry background, low quality, text, watermark"

    final_prompt = f"{prompt}, {style}. Negative: {negative}"

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.images.generate(
            model="gemini-2.5-flash-image",
            prompt=final_prompt,
            n=1,
            size="1024x1024",
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка генерации: {e}")

    if not response.data:
        raise RuntimeError("API не вернул данные")

    data = response.data[0]

    # Пробуем получить URL
    image_url = getattr(data, 'url', None)
    if image_url:
        # Скачиваем по URL
        try:
            resp = requests.get(image_url, timeout=30)
            resp.raise_for_status()
            img_data = resp.content
        except Exception as e:
            raise RuntimeError(f"Не удалось скачать картинку по URL: {e}")
    else:
        # Если URL нет, пробуем получить base64
        b64 = getattr(data, 'b64_json', None)
        if b64:
            try:
                img_data = base64.b64decode(b64)
            except Exception as e:
                raise RuntimeError(f"Не удалось декодировать base64: {e}")
        else:
            # Если нет ни url, ни b64_json – выводим содержимое ответа для отладки
            raise RuntimeError(f"Неизвестный формат ответа: {data}")

    # Сохраняем изображение
    try:
        image = Image.open(BytesIO(img_data))
        image.save(output_path)
    except Exception as e:
        raise RuntimeError(f"Ошибка сохранения: {e}")

    return output_path
