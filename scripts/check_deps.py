import importlib
import sys
import os

# Special handling for package names that differ from their import names
PACKAGE_TO_MODULE_MAP = {
    "python-dotenv": "dotenv",
    # Add other mappings here if needed, e.g.:
    # "beautifulsoup4": "bs4",
    # "PyYAML": "yaml",
}

if __name__ == "__main__":
    # When scripts/check_deps.py is run from project root as `python scripts/check_deps.py`,
    # __file__ is scripts/check_deps.py. os.path.dirname(__file__) is scripts/.
    # So, project root is os.path.join(os.path.dirname(__file__), '..')
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
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
                package_name_in_req = line.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip()
                if not package_name_in_req: # Handle empty lines or malformed entries
                    continue
                
                module_to_import = PACKAGE_TO_MODULE_MAP.get(package_name_in_req, package_name_in_req)
                
                try:
                    importlib.import_module(module_to_import)
                    # print(f"Successfully imported {package_name_in_req}") # Optional: for verbose success
                except ImportError:
                    failed_imports.append(f"{package_name_in_req} (tried to import '{module_to_import}')")
                except Exception as e:
                    failed_imports.append(f"{package_name_in_req} (tried to import '{module_to_import}', unexpected error: {e})")

    if not failed_imports:
        print("OK_DEPS")
        sys.exit(0)
    else:
        print(f"ERROR_DEPS: Failed to import the following packages: {', '.join(failed_imports)}")
        sys.exit(1) 