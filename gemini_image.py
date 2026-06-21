import os
import requests
import base64
from io import BytesIO
from PIL import Image

def generate_image(prompt: str, output_path: str = "generated_image.png") -> str:
    """
    Генерирует изображение через API OnlySq (ImaGen).
    Документация: https://docs.onlysq.ru/#imagen
    """
    api_key = os.getenv("ONLYSQ_API_KEY")
    if not api_key:
        raise ValueError("ONLYSQ_API_KEY не задан в переменных окружения")

    # 1. Настройки API
    url = "https://api.onlysq.ru/ai/imagen"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 2. Формируем промт с вашими стилями
    style = "full body shot, anime style, High quality, Flat colour anime style image showing, high quality image, 8k, ultra UHD, clear image, sharp lines, highly detailed image, realistic anatomy, perfectly realistic hands, anime nose, realistic leg length, No People in the background"
    final_prompt = f"{prompt}, {style}."

    # 3. Параметры запроса (модель и соотношение сторон)
    model = os.getenv("ONLYSQ_IMAGE_MODEL", "flux")  # или "sdxl", "turbo"
    ratio = os.getenv("ONLYSQ_IMAGE_RATIO", "1:1")   # 1:1, 16:9, 9:16 и т.д.

    payload = {
        "model": model,
        "prompt": final_prompt,
        "ratio": ratio
    }

    # 4. Отправляем запрос
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()  # выбросит исключение при HTTP-ошибке
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ошибка запроса к API: {e}")

    # 5. Разбираем ответ
    data = response.json()

    # Проверяем, есть ли поле "files" и не пустое ли оно
    if not data.get("files"):
        # Если есть сообщение об ошибке — покажем его
        error_msg = data.get("error", {}).get("message", "Неизвестная ошибка")
        raise RuntimeError(f"API не вернул изображение: {error_msg}")

    # 6. Декодируем base64 и сохраняем
    try:
        # Берём первую картинку из списка
        image_base64 = data["files"][0]
        image_data = base64.b64decode(image_base64)
    except Exception as e:
        raise RuntimeError(f"Ошибка декодирования изображения: {e}")

    try:
        # Сохраняем на диск через PIL для проверки целостности
        image = Image.open(BytesIO(image_data))
        image.save(output_path)
    except Exception as e:
        raise RuntimeError(f"Ошибка сохранения изображения: {e}")

    return output_path
