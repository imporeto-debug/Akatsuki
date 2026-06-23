import os
import requests
import base64
from io import BytesIO
from PIL import Image

def generate_image(prompt: str, output_path: str = "generated_image.png") -> str:
    api_key = os.getenv("ONLYSQ_API_KEY")
    if not api_key:
        raise ValueError("ONLYSQ_API_KEY не задан")

    url = "https://api.onlysq.ru/ai/imagen"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # ---------- ВАШ ПОЛНЫЙ СТИЛЬ (без негатива) ----------
    style = "full body shot, anime style, gouache painting, rich paint strokes, vibrant colors, artistic canvas art, well proportioned anatomy, masterpiece, high quality"
    final_prompt = f"Draw exactly this: {prompt}. {style}"

    # ---------- ПАРАМЕТРЫ (из переменных окружения) ----------
    model = os.getenv("ONLYSQ_IMAGE_MODEL", "stable-diffusion-xl-base-1.0")
    ratio = os.getenv("ONLYSQ_IMAGE_RATIO", "1:1")

    payload = {
        "model": model,
        "prompt": final_prompt,
        "ratio": ratio
    }

    # ---------- ЗАПРОС ----------
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ошибка API: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ошибка соединения: {e}")

    data = response.json()
    if not data.get("files"):
        error_msg = data.get("error", {}).get("message", "Неизвестная ошибка")
        raise RuntimeError(f"API не вернул изображение: {error_msg}")

    # ---------- СОХРАНЕНИЕ ----------
    try:
        image_base64 = data["files"][0]
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        image.save(output_path)
    except Exception as e:
        raise RuntimeError(f"Ошибка при сохранении: {e}")

    return output_path
