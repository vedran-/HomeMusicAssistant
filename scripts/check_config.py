import sys
import os

# Adjust path to import from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.config.settings import load_settings, AppSettings

if __name__ == "__main__":
    config_file = os.path.join(project_root, "config.json")
    try:
        settings: AppSettings = load_settings(config_file)
        # Perform a basic check, e.g., that a key setting is present
        if settings.paths and settings.paths.autohotkey_exe:
            print("OK_CONFIG")
            sys.exit(0)
        else:
            print("ERROR_CONFIG: Essential path settings missing after load.")
            sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR_CONFIG: File not found - {e}")
        sys.exit(1)
    except ValueError as e: # Pydantic validation error or other value errors
        print(f"ERROR_CONFIG: Validation error - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR_CONFIG: Unexpected error - {e}")
        sys.exit(1) 