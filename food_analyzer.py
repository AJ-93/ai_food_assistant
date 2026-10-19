import base64
import io
import json
import os
import torch

from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from models import FoodAnalysis
from utils import load_config
from PIL import Image
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from transformers import (
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
    pipeline,
)

PATH_TO_CONFIG = Path(__file__).parent / 'configration.yaml'
SYS_PROMPT_PATH = Path(__file__).parent / 'prompts' /'system.txt.j2'
VOICE_SYS_PROMPT_PATH = Path(__file__).parent / 'prompts' /'system_voice.txt.j2'
USER_PROMPT_PATH = Path(__file__).parent / 'prompts' / 'user.txt.j2'
PROMPT_PATH = Path(__file__).parent / 'prompts'

env = Environment(
    loader=FileSystemLoader(PROMPT_PATH),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)
TEMPLATE_VOICE_USER_PROMPT = env.get_template("user_voice.txt.j2")


load_dotenv()

config = load_config(PATH_TO_CONFIG)

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
MODEL = config['LLM_Config']['IMAGE_MODEL']
VOICE_MODEL = config['LLM_Config']['VOICE_MODEL']
SYSTEM_PROMPT = SYS_PROMPT_PATH.read_text(encoding="utf-8")
USER_PROMPT = USER_PROMPT_PATH.read_text(encoding="utf-8")

def get_transcriber_model():

    if torch.cuda.is_available():
        device = "cuda:0"
        torch_dtype = torch.float16
    elif(
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        device = "mps"
        torch_dtype = torch.float32
    else:
        device = "cpu"
        torch_dtype = torch.float32

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID=VOICE_MODEL,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
    )

    model.to(device)

    processor = AutoProcessor.from_pretrained(ModelID=VOICE_MODEL)

    _transcriber = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
        )

    return _transcriber


def transcribe_audio(audio_file_path: str):
    if not audio_file_path:
        raise ValueError("No audio recording provided")

    transcriber = get_transcriber_model()

    result = transcriber(audio_file_path)

    transcript = result["text"].strip()

    if not transcript:
        raise ValueError("Speech could not be recognized")

    return transcript


def analyze_food_image(image_path: str):
    with Image.open(image_path) as f:
        f = f.convert('RGB')

        f.thumbnail((1600, 1600))

        buffer = io.BytesIO()
        f.save(buffer, format='JPEG', quality=85)
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')

        response = client.chat.completions.create(
            model=MODEL,
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

def analyze_food_audio(description: str):
    if not description or not description.strip():
        raise ValueError("Empty description provided")

    VOICE_USER_PROMPT = TEMPLATE_VOICE_USER_PROMPT.render(description)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": VOICE_SYS_PROMPT_PATH,
            },
            {
                "role": "user",
                "content": VOICE_USER_PROMPT,
            },
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from LLM")

    return FoodAnalysis.model_validate_json(content)

def analyze_food(input_data: str, input_type: str):
    if input_type == "voice":
        transcript = transcribe_audio(input_data)
        return analyze_food_audio(transcript)
    elif input_type == "image":
        return analyze_food_image(input_data)

    raise ValueError(f"Unsupported data type {input_type}")
