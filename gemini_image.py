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
    negative = "giant head, big head, disproportionate body, close-up, cropped, portrait, avoiding 3d render, photorealism, real life photo, blurry background, low quality, text, watermark"
    final_prompt = f"{prompt}, {style}. Negative: {negative}"
    
    # ---------- ФОРМИРУЕМ ПРОМТ: СНАЧАЛА ЗАПРОС ПОЛЬЗОВАТЕЛЯ ----------
    # Добавляем команду "Draw exactly this:" чтобы модель точно поняла, что рисовать
    final_prompt = f"Draw exactly this: {prompt}. {style}"

    # ---------- ПАРАМЕТРЫ ----------
    model = os.getenv("ONLYSQ_IMAGE_MODEL", "nano-banana-pro")
    ratio = os.getenv("ONLYSQ_IMAGE_RATIO", "2:3")  # вертикальный для персонажей

    payload = {
        "model": model,
        "prompt": final_prompt,
        "ratio": ratio
        # негативный промпт УДАЛЁН
    }

    # ---------- ЗАПРОС ----------
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    if not data.get("files"):
        error_msg = data.get("error", {}).get("message", "Неизвестная ошибка")
        raise RuntimeError(f"API не вернул изображение: {error_msg}")

    # ---------- СОХРАНЕНИЕ ----------
    image_base64 = data["files"][0]
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))
    image.save(output_path)
    return output_path
