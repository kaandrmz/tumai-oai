from typing import Dict
from pathlib import Path

current_dir = Path(__file__).parent
PROMPTS_FOLDER = current_dir

def get_prompt(prompt_name: str, vars: Dict[str, str]) -> str:
    with open(PROMPTS_FOLDER / f"{prompt_name}.txt", "r") as file:
        prompt = file.read()
    for key, value in vars.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", value)
    return prompt
