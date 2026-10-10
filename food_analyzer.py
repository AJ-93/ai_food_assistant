import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from models import FoodAnalysis
from utils import load_config

PATH_TO_CONFIG = Path(__file__).parent / 'configration.yaml'

load_dotenv()

config = load_config(PATH_TO_CONFIG)

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
MODEL = config['LLM_Config']['MODEL']




