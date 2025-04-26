from pathlib import Path
import sys
from dotenv import load_dotenv

# env
current_file_dir = Path(__file__).resolve().parent

# add project to path
project_path = current_file_dir.parent
print(f'Adding {project_path} to sys.path')
sys.path.append(str(project_path))

env_path = project_path / '.env'
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
print(f'Loaded env from {env_path}')
