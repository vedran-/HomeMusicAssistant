import importlib
import sys
import os

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    requirements_file = os.path.join(project_root, "requirements.txt")
    
    if not os.path.exists(requirements_file):
        print(f"ERROR_DEPS: requirements.txt not found at {requirements_file}")
        sys.exit(1)

    failed_imports = []
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Basic parsing for package name (e.g., before '==', '>=', '[')
                package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip()
                if not package_name: # Handle empty lines or malformed entries
                    continue
                try:
                    importlib.import_module(package_name)
                    # print(f"Successfully imported {package_name}") # Optional: for verbose success
                except ImportError:
                    failed_imports.append(package_name)
                except Exception as e:
                    failed_imports.append(f"{package_name} (unexpected error: {e})")

    if not failed_imports:
        print("OK_DEPS")
        sys.exit(0)
    else:
        print(f"ERROR_DEPS: Failed to import the following packages: {', '.join(failed_imports)}")
        sys.exit(1) 