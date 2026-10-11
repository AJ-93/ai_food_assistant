import base64
import io
import json
import os

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from models import FoodAnalysis
from utils import load_config
from PIL import Image

PATH_TO_CONFIG = Path(__file__).parent / 'configration.yaml'
SYS_PROMPT_PATH = Path(__file__).parent / 'prompts' /'system.txt.j2'
USER_PROMPT_PATH = Path(__file__).parent / 'prompts' / 'user.txt.j2'

load_dotenv()

config = load_config(PATH_TO_CONFIG)

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
MODEL = config['LLM_Config']['MODEL']
SYSTEM_PROMPT = SYS_PROMPT_PATH.read_text(encoding="utf-8")
USER_PROMPT = USER_PROMPT_PATH.read_text(encoding="utf-8")

def analyze_food(image_path: str):
    with Image.open(image_path) as f:
        f = f.convert('RGB')

        f.thumbnail((1600, 1600))

        buffer = io.BytesIO()
        f.save(buffer, format='JPEG', quality=85)
        encoded = base64.b64encode(buffer.getvalue().decode('utf-8'))

        response = client.chat.completions.create(
            MODEL=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": USER_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from LLM")

    data = json.loads(content)

    return FoodAnalysis.model_validate(data)