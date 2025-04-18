"""This figures out what packages you have to install to in order to make all .py and .ipynb files in and below current directory work.

Copy this script's output to requirements.txt and then install the packages with:

   uv pip install -r requirements.txt

This script might produce warnings about bad python imports: resolve them first before running pip install above."""

import os
import ast
import sys
import subprocess
from typing import Dict, List, Tuple, DefaultDict
from collections import defaultdict

try:
    import nbformat
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nbformat"])
    import nbformat

try:
    import stdlib_list
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "stdlib-list"])
    import stdlib_list

# Edit this when you find packages that this script warns you it can't figure out.
# You, yourself, can "figure it out" by asking Perplexity what installs
# are needed to satisfy the problem import statments.
MANUAL_MAPPINGS: Dict[str, str] = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
    "google": "google-api-python-client",
    "win32serviceutil": "pywin32",
    "win32service": "pywin32",
    "win32event": "pywin32",
}

def get_pypi_name(import_name: str) -> str:
    return MANUAL_MAPPINGS.get(import_name, import_name)

def get_local_modules(root_dir: str) -> set:
    local_modules = set()
    for dirpath, _, filenames in os.walk(root_dir):
        if "__init__.py" in filenames:
            local_modules.add(os.path.basename(dirpath))
        for filename in filenames:
            if filename.endswith('.py') and filename != "__init__.py":
                local_modules.add(filename[:-3])
    return local_modules

def extract_imports(filepath: str) -> List[Tuple[str, int, str]]:
    imports = []
    try:
        if filepath.endswith('.py'):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif filepath.endswith('.ipynb'):
            with open(filepath, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
            content = '\n'.join(cell.source for cell in nb.cells if cell.cell_type == 'code')
        else:
            return imports
    except Exception:
        return imports

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split('.')[0]
                imports.append((
                    top_level,
                    node.lineno,
                    f"import {alias.name}",
                    filepath
                ))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top_level = node.module.split('.')[0]
                imports.append((
                    top_level,
                    node.lineno,
                    f"from {node.module} import ...",
                    filepath
                ))
    return imports

def check_pypi(package: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--dry-run', package],
            capture_output=True,
            text=True,
            check=True
        )
        return True, ''
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def main():
    root_dir = '.'  # Set to your project directory if different
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    std_libs = set(stdlib_list.stdlib_list(py_version))
    local_modules = get_local_modules(root_dir)

    # Structure: {pypi_name: List[(import_name, lineno, import_line, filepath)]}
    package_map: DefaultDict[str, List[Tuple]] = defaultdict(list)

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(('.py', '.ipynb')):
                filepath = os.path.join(dirpath, filename)
                for import_name, lineno, import_line, fpath in extract_imports(filepath):
                    if (import_name not in std_libs and
                        import_name not in sys.builtin_module_names and
                        import_name not in local_modules and
                        not import_name.startswith('_')):
                        
                        pypi_name = get_pypi_name(import_name)
                        package_map[pypi_name].append((
                            import_name, lineno, import_line, fpath
                        ))

    valid = []
    invalid = []
    for pkg, locations in package_map.items():
        is_valid, error = check_pypi(pkg)
        if is_valid:
            valid.append(pkg)
        else:
            invalid.append((pkg, locations, error))

    print("\n=== VALID PACKAGES ===")
    for pkg in valid:
        print(f"  {pkg}")

    if invalid:
        print("\n=== INVALID/UNKNOWN PACKAGES ===")
        for pkg, locations, error in invalid:
            print(f"\n⚠️  {pkg}: {error.splitlines()[-1]}")
            print("Found in:")
            for imp_name, lineno, import_line, fpath in locations:
                print(f"  {fpath}:{lineno}")
                print(f"    {import_line} (original import: {imp_name})")

    print("\nValidation complete. Copy valid packages to requirements.txt:")

if __name__ == "__main__":
    main()
