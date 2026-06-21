import os
import requests
from io import BytesIO
from PIL import Image
from openai import OpenAI

def generate_image(prompt: str, output_path: str = "generated_image.png") -> str:
    """Генерирует изображение через RiftAI. 

    Автоматически распознает персонажей Наруто, рисует в полный рост и в стиле гуаши.
    """

    api_key = os.getenv("RIFT_API_KEY")
    base_url = os.getenv("RIFT_BASE_URL", "https://riftai.su")

    if not api_key:
        raise ValueError(
            "Ошибка: Переменная окружения RIFT_API_KEY не задана на хостинге Bothost."
        )

    # 1. Добавляем к запросу пользователя явное указание, что это персонаж из Наруто,
    # а также стиль аниме-гуаши и полный рост.
    anime_gouache_style = "character from Naruto anime, full body shot, anime style, gouache painting, rich paint strokes, vibrant colors, artistic canvas art, well proportioned anatomy, masterpiece, high quality"

    # 2. Негативный промт против огромных голов, портретов и плохого качества
    negative_prompt = "giant head, big head, disproportionate body, close-up, cropped, portrait, avoiding 3d render, photorealism, real life photo, blurry background, low quality, text, watermark"

    # 3. Соединяем запрос (например, "Саске в плаще") со скрытыми настройками
    final_prompt = (
        f"{prompt}, {anime_gouache_style}. Negative: {negative_prompt}"
    )

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.images.generate(
        model="gemini-2.5-flash-image",
        prompt=final_prompt,
        n=1,
        size="1024x1024",
    )

    image_url = response.data.url
    if not image_url:
        raise ValueError("Адрес изображения не получен от API.")

    img_data = requests.get(image_url).content
    image = Image.open(BytesIO(img_data))
    image.save(output_path)

    return output_path
