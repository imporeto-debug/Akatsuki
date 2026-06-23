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
    # Я убрал только "No People in the background", остальное оставил
    style = "full body shot, cinematic lighting, high quality, ultra UHD, realistic, intense, enhanced contrast, highly detailed skin detailed character design concept art, highly detailed image, realistic anatomy, perfectly realistic hands, realistic leg length, correct number of fingers, five fingers, perfectly proportioned limbs, natural poses, accurate human anatomy, no extra fingers, no extra limbs"

    # ---------- ФОРМИРУЕМ ПРОМТ: СНАЧАЛА ЗАПРОС ПОЛЬЗОВАТЕЛЯ ----------
    # Добавляем команду "Draw exactly this:" чтобы модель точно поняла, что рисовать
    final_prompt = f"Draw exactly this: {prompt}. {style}"

    # ---------- ПАРАМЕТРЫ ----------
    model = os.getenv("ONLYSQ_IMAGE_MODEL", "flux-2-max")
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
