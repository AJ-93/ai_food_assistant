from pathlib import Path
import yaml

def load_config(config_path: Path):
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with config_path.open() as f:
        data = yaml.safe_load(f)
    return data