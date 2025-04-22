"""This figures out what packages you have to install to in order to make all .py and .ipynb files in and below current directory work.

Run without arguments to print potential requirements to the console.
Use the --output <filename> option to write the requirements to a file.

Example Usage:
  python find_reqs.py
  python find_reqs.py --output requirements.txt

Copy the output or the generated file's content, review it, and then install with:

   uv add -r <your_requirements_file>.txt

or (BUT NOT DESIRABLY)

   uv pip install -r <your_requirements_file>.txt

(using uv pip install doesn't update the toml file)

This script might produce warnings about bad python imports: resolve them first before running pip install above."""

import os
import ast
import sys
import subprocess
# --- Added for PyPI API check ---
import urllib.request
import urllib.error
import json
# --- Added for Command Line Args ---
import argparse
# --- End Added ---
from typing import Dict, List, Tuple, DefaultDict
from collections import defaultdict

try:
    import nbformat
except ImportError:
    print("Installing nbformat...", file=sys.stderr)
    # Use check_call to ensure it finishes before proceeding
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nbformat"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) # Hide pip output unless error
    import nbformat

try:
    import stdlib_list
except ImportError:
    print("Installing stdlib-list...", file=sys.stderr)
    # Use check_call to ensure it finishes before proceeding
    subprocess.check_call([sys.executable, "-m", "pip", "install", "stdlib-list"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) # Hide pip output unless error
    import stdlib_list

# Edit this when you find packages that this script warns it can't figure out.
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
    # Add mappings for known namespace packages if needed
    # e.g., "azure.storage.blob": "azure-storage-blob"
}

def get_pypi_name(import_name: str) -> str:
    """Gets the likely PyPI package name, applying manual mappings."""
    # Check for exact match first (case-sensitive might matter for some imports)
    if import_name in MANUAL_MAPPINGS:
        return MANUAL_MAPPINGS[import_name]
    # Check for lowercase match
    lower_import_name = import_name.lower()
    if lower_import_name in MANUAL_MAPPINGS:
         return MANUAL_MAPPINGS[lower_import_name]
    # Default to the original import name if no mapping found
    return import_name

def get_local_modules(root_dir: str) -> set:
    """Finds potential local module names based on file/directory structure."""
    local_modules = set()
    abs_root = os.path.abspath(root_dir)
    excluded_dirs = {'.venv', 'venv', 'env', '.env', '__pycache__', '.git', '.hg', '.svn', 'build', 'dist', 'docs', 'tests', 'test', 'site-packages', 'node_modules', '.vscode', '.idea', 'data', 'logs', 'output', 'results'}

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        # Modify dirnames in place to prevent descending into excluded directories
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs and not d.startswith('.')]

        # Add directories containing __init__.py (packages)
        if "__init__.py" in filenames:
            package_name = os.path.basename(dirpath)
            # Avoid adding the root dir itself if it's just '.'
            if os.path.abspath(dirpath) != abs_root:
                 local_modules.add(package_name)

        # Add .py files (modules)
        for filename in filenames:
            if filename.endswith('.py') and filename != "__init__.py":
                local_modules.add(filename[:-3])

    return local_modules


def extract_imports(filepath: str) -> List[Tuple[str, int, str, str]]:
    """Extracts top-level imports from a Python or Jupyter Notebook file."""
    imports = [] # Initialize list to hold imports found in this file
    content = None # Content variable primarily for .py files

    # --- Read File Content ---
    try:
        if filepath.endswith('.py'):
            # Try utf-8 first, then fallback with error handling
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                 try:
                    # Try system default encoding or latin-1 as fallback
                    with open(filepath, 'r', encoding=sys.getdefaultencoding(), errors='ignore') as f:
                        content = f.read()
                    print(f"Warning: File {filepath} not utf-8, read with default encoding.", file=sys.stderr)
                 except Exception as e_fallback:
                    print(f"Warning: Could not decode file {filepath} with utf-8 or default encoding. Skipping. Error: {e_fallback}", file=sys.stderr)
                    return [] # Return empty list if file can't be read

        # IPYNB handling happens below, no need to read content here

    except FileNotFoundError:
        print(f"Warning: File not found during import extraction: {filepath}", file=sys.stderr)
        return []
    except Exception as e: # Catch other potential file reading errors like permission denied
        print(f"Warning: Error reading file {filepath}: {e}", file=sys.stderr)
        return []

    # --- Process IPYNB Files Cell by Cell with Line Filtering ---
    if filepath.endswith('.ipynb'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
        except nbformat.validator.NotebookValidationError as e:
             print(f"Warning: Skipping invalid notebook {filepath}. Validation Error: {e.message}", file=sys.stderr)
             return [] # Return empty list for this notebook
        except Exception as e:
             print(f"Warning: Error reading notebook {filepath}: {e}", file=sys.stderr)
             return [] # Return empty list for this notebook

        # Process cell by cell
        cell_no = 0 # Use cell index for reporting
        for cell_index, cell in enumerate(nb.cells):
            cell_no = cell_index + 1 # 1-based index for user messages
            if cell.cell_type == 'code' and cell.source:
                cell_content = cell.source
                lines = cell_content.splitlines()
                python_lines = []

                # --- Filter out ALL Lines Starting with Magics (%) or Shell Commands (!) ---
                for line in lines:
                    stripped_line = line.strip()
                    # Keep the line if it doesn't start with % or !
                    if not stripped_line.startswith('%') and not stripped_line.startswith('!'):
                        python_lines.append(line) # Keep original line with indentation

                # Rebuild the filtered content for this cell
                filtered_content = '\n'.join(python_lines)

                # Skip parsing if filtering removed all content or only left whitespace/comments
                if not filtered_content.strip():
                    continue # Move to the next cell

                # --- Attempt to Parse the Filtered Cell Content ---
                try:
                    # Parse this individual cell's filtered content
                    parse_filename = f"{filepath}#cell{cell_no}(filtered)"
                    tree = ast.parse(filtered_content, filename=parse_filename)

                    # Walk the AST *of this filtered cell* to find imports
                    for node in ast.walk(tree):
                        import_info = None
                        line_no = node.lineno if hasattr(node, 'lineno') else 0

                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                top_level = alias.name.split('.')[0]
                                if top_level:
                                    import_info = (
                                        top_level, line_no, f"import {alias.name}",
                                        f"{filepath}#cell{cell_no}" # Indicate originating cell
                                    )
                                    imports.append(import_info)
                        elif isinstance(node, ast.ImportFrom):
                            if node.level == 0 and node.module:
                                top_level = node.module.split('.')[0]
                                if top_level:
                                    imported_names = ", ".join(a.name for a in node.names)
                                    import_line = f"from {node.module} import {imported_names}"
                                    import_info = (
                                        top_level, line_no, import_line,
                                        f"{filepath}#cell{cell_no}" # Indicate originating cell
                                    )
                                    imports.append(import_info)
                except SyntaxError as e:
                    # Syntax error *even after filtering*
                    cell_line = e.lineno if hasattr(e, 'lineno') else '?'
                    print(f"Warning: Skipping cell {cell_no} in {filepath} due to SyntaxError after filtering magics (near line ~{cell_line}): {e.msg}. Cell might contain complex syntax or unfilterable magics.", file=sys.stderr)
                    # Uncomment below to debug the filtered content that failed parsing
                    # print(f"--- Filtered Content Cell {cell_no} Start ---", file=sys.stderr)
                    # print(filtered_content, file=sys.stderr)
                    # print(f"--- Filtered Content Cell {cell_no} End ---", file=sys.stderr)
                    continue # Move to the next cell
                except Exception as e:
                    # Other AST parsing errors for this cell
                    print(f"Warning: Could not parse AST for filtered cell {cell_no} in {filepath}: {e}. Skipping cell.", file=sys.stderr)
                    continue # Move to the next cell

        # After checking all cells in the notebook, return the accumulated imports for THIS notebook
        return imports
        # --- End IPYNB Handling ---

    # --- Process Python (.py) Files ---
    elif filepath.endswith('.py'):
        if not content: # Handle empty or unreadable python files
             return []
        try:
            tree = ast.parse(content, filename=filepath)
            # Walk the tree for the Python file
            py_imports = [] # Use a separate list for clarity
            for node in ast.walk(tree):
                import_info = None
                line_no = node.lineno if hasattr(node, 'lineno') else 0

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_level = alias.name.split('.')[0]
                        if top_level:
                            import_info = (top_level, line_no, f"import {alias.name}", filepath)
                            py_imports.append(import_info)
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        top_level = node.module.split('.')[0]
                        if top_level:
                            imported_names = ", ".join(a.name for a in node.names)
                            import_line = f"from {node.module} import {imported_names}"
                            import_info = (top_level, line_no, import_line, filepath)
                            py_imports.append(import_info)
            return py_imports # Return imports found in the .py file

        except SyntaxError as e:
            line = e.lineno if hasattr(e, 'lineno') else '?'
            offset = e.offset if hasattr(e, 'offset') else '?'
            print(f"Warning: SyntaxError in {filepath} (line {line}, offset {offset}). Skipping file. Error: {e.msg}", file=sys.stderr)
            return [] # Return empty list for this file
        except Exception as e:
            print(f"Warning: Could not parse AST for {filepath}: {e}. Skipping file.", file=sys.stderr)
            return [] # Return empty list for this file

    # If file extension is neither .py nor .ipynb
    else:
        # This case should ideally not be reached if main() filters correctly
        print(f"Info: Skipping file with unhandled extension: {filepath}", file=sys.stderr)
        return []


# --- New function using PyPI API ---
def check_pypi_via_api(package: str) -> Tuple[bool, str]:
    """Checks if a package exists on PyPI using the JSON API."""
    # Normalize package name according to PEP 503
    normalized_package = package.lower().replace("_", "-")
    url = f"https://pypi.org/pypi/{normalized_package}/json"
    headers = {'User-Agent': 'Python-Package-Requirement-Finder/1.2 (Language=Python)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response: # Added timeout
            if response.status == 200:
                 response.read(10) # Minimal check to confirm connection worked
                 return True, ''
            else:
                return False, f"Received non-200 status: {response.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"Package '{normalized_package}' not found on PyPI (404)"
        else:
            return False, f"HTTP Error {e.code} when checking PyPI for '{normalized_package}': {e.reason}"
    except urllib.error.URLError as e:
        reason_str = str(e.reason) if hasattr(e, 'reason') else "Unknown network error"
        return False, f"Network error checking PyPI for '{normalized_package}': {reason_str}"
    except TimeoutError:
         return False, f"Timeout occurred while checking PyPI for '{normalized_package}'"
    except Exception as e:
        return False, f"Unexpected error checking PyPI for '{normalized_package}': {type(e).__name__} - {e}"

def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Find potential package requirements by scanning .py and .ipynb files.",
        formatter_class=argparse.RawDescriptionHelpFormatter # Keep help formatting
    )
    parser.add_argument(
        '-o', '--output',
        metavar='FILENAME',
        type=str,
        help="Write the list of valid packages (one per line) to the specified file."
    )
    parser.add_argument(
        '-d', '--dir',
        metavar='DIRECTORY',
        type=str,
        default='.', # Default to current directory
        help="The root directory to scan (default: current directory)."
    )
    args = parser.parse_args()
    output_file = args.output
    root_dir = args.dir
    # --- End Argument Parsing ---


    print(f"Scanning for Python and Notebook files in: {os.path.abspath(root_dir)}", file=sys.stderr)
    if not os.path.isdir(root_dir):
        print(f"Error: Specified directory '{root_dir}' not found or is not a directory.", file=sys.stderr)
        sys.exit(1)


    try:
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        std_libs = set(stdlib_list.stdlib_list(py_version))
        std_libs.update(sys.builtin_module_names)
        std_libs.update({'typing', 'os', 'sys', 're', 'json', 'datetime', 'math', 'collections', 'argparse', 'logging', 'pathlib'}) # Add obviously standard libs
        print(f"Using standard library list for Python {py_version}", file=sys.stderr)
    except Exception as e:
        print(f"Error: Could not get standard library list. Check 'stdlib-list' installation.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        local_modules = get_local_modules(root_dir)
        print(f"Identified {len(local_modules)} potential local modules/packages.", file=sys.stderr)
    except Exception as e:
         print(f"Error: Failed to identify local modules.", file=sys.stderr)
         print(f"Details: {e}", file=sys.stderr)
         sys.exit(1)


    # Structure: {pypi_name: List[(import_name, lineno, import_line, filepath)]}
    package_map: DefaultDict[str, List[Tuple[str, int, str, str]]] = defaultdict(list)
    files_processed = 0
    all_imports_found = 0
    files_scanned = 0 # Track total files encountered

    excluded_dirs_walk = {'.venv', 'venv', 'env', '.env', '__pycache__', '.git', '.hg', '.svn', 'build', 'dist', 'docs', 'tests', 'test', 'site-packages', 'node_modules', '.vscode', '.idea', 'data', 'logs', 'output', 'results'}

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs_walk and not d.startswith('.')]

        for filename in filenames:
            files_scanned += 1
            if filename.endswith(('.py', '.ipynb')):
                filepath = os.path.join(dirpath, filename)
                # Skip processing the script itself
                try:
                    # Use realpath to handle symlinks consistently
                    if os.path.samefile(os.path.realpath(filepath), os.path.realpath(__file__)):
                        continue
                except FileNotFoundError:
                    pass # Handle if __file__ is not found or path issue
                except OSError:
                    pass # Handle potential errors comparing files

                files_processed += 1
                extracted = extract_imports(filepath) # Call the updated function
                for import_name, lineno, import_line, fpath_info in extracted:
                    all_imports_found += 1
                    # Basic filtering
                    if (import_name and # Ensure not empty
                        import_name not in std_libs and
                        import_name not in local_modules and
                        not import_name.startswith('_')): # Ignore "private" imports

                        pypi_name = get_pypi_name(import_name)
                        # Store fpath_info which might include cell number for notebooks
                        package_map[pypi_name].append((
                            import_name, lineno, import_line, fpath_info
                        ))

    print(f"Scanned {files_scanned} total files. Processed {files_processed} Python/Notebook files, found {all_imports_found} total import statements.", file=sys.stderr)
    print(f"Found {len(package_map)} unique potential external package dependencies.", file=sys.stderr)

    valid = []
    invalid = []
    print(f"\n--- Checking {len(package_map)} potential packages against PyPI ---", file=sys.stderr)
    # Use the API checker
    packages_to_check = sorted(list(package_map.keys())) # Check in alphabetical order
    total_packages = len(packages_to_check)
    for i, pkg in enumerate(packages_to_check):
        print(f"Checking PyPI [{i+1}/{total_packages}]: {pkg:<30}...", end='\r', file=sys.stderr)
        is_valid, error_msg = check_pypi_via_api(pkg)
        locations = package_map[pkg]
        if is_valid:
            valid.append(pkg)
            print(f"Checking PyPI [{i+1}/{total_packages}]: {pkg:<30}... Found ✅", file=sys.stderr)
        else:
            invalid.append((pkg, locations, error_msg))
            print(f"Checking PyPI [{i+1}/{total_packages}]: {pkg:<30}... Not Found/Error ❌", file=sys.stderr)

    print(" " * 70, end='\r', file=sys.stderr)
    print("\n--- PyPI Check Complete ---", file=sys.stderr)


    # --- Output Results ---
    valid.sort()
    invalid.sort(key=lambda x: x[0])

    print("\n# == Potential Requirements (found on PyPI) ==")
    if valid:
        for pkg in valid:
            print(f"{pkg}") # Print directly, one per line
    else:
        print("# (None found)")
    print("# ============================================")


    if output_file:
        print(f"\nWriting {len(valid)} valid packages to: {output_file}", file=sys.stderr)
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if valid:
                    f.write("# Requirements generated by find_reqs.py\n")
                    f.write("# Review carefully before installing.\n")
                    for pkg in valid:
                        f.write(f"{pkg}\n")
                else:
                    f.write("# No valid requirements found by find_reqs.py.\n")
            print(f"Successfully wrote requirements to {output_file}", file=sys.stderr)
        except IOError as e:
            print(f"\nError: Could not write to output file {output_file}: {e}", file=sys.stderr)
            print("\nValid packages found (failed to write to file):", file=sys.stderr)
            if valid:
                 for pkg in valid: print(f"  {pkg}", file=sys.stderr)
            else:
                 print("  (None)", file=sys.stderr)


    if invalid:
        print("\n# == Issues Found (Not Found on PyPI or Check Error) ==", file=sys.stderr)
        for pkg, locations, error in invalid:
            print(f"\n# --- Package: {pkg} ---", file=sys.stderr)
            print(f"# Check Result: {error}", file=sys.stderr)
            print(f"# Potentially imported as (showing unique locations):", file=sys.stderr)
            # Sort locations for consistency & get unique import points
            # Note: lineno might be less accurate for filtered notebook cells
            locations.sort(key=lambda x: (x[3], x[1])) # Sort by file/cell info, then line number
            unique_imports_str = set()
            for imp_name, lineno, _import_line, fpath_info in locations:
                 # Use relative path for display
                 try:
                    # Handle potential '#cellX' suffix for notebooks
                    base_fpath = fpath_info.split('#')[0]
                    cell_suffix = f" ({fpath_info.split('#')[1]})" if '#' in fpath_info else ""
                    rel_path = os.path.relpath(base_fpath, root_dir)
                    loc_display = f"'./{rel_path}{cell_suffix}'"
                 except ValueError: # Handle cases where relpath might fail
                    loc_display = f"'{fpath_info}'" # Fallback to full path info

                 unique_imports_str.add(f"'{imp_name}' in {loc_display} (approx line {lineno})")

            for loc_str in sorted(list(unique_imports_str)):
                 print(f"#   - {loc_str}", file=sys.stderr)
        print("# ======================================================", file=sys.stderr)


    print("\nFinished.", file=sys.stderr)
    if not output_file and valid:
        print("\nSuggestion: Rerun with '--output <filename>' to save the requirements.", file=sys.stderr)
    elif output_file and valid:
        print(f"\nSuggestion: Review the generated file '{output_file}' and install using 'uv add -r {output_file}'.", file=sys.stderr)

    if invalid:
        print("\nSuggestion: Review the packages listed under 'Issues Found' above (printed to stderr).", file=sys.stderr)
        print("  - Check for typos in your import statements.", file=sys.stderr)
        print("  - If the import name is correct but differs from the package name (e.g., 'PIL' vs 'pillow'), add it to MANUAL_MAPPINGS in the script.", file=sys.stderr)
        print("  - If the package check failed (e.g., network error), verify manually or retry.", file=sys.stderr)
        print("  - Ensure the listed imports aren't actually local modules missed by the scanner (check 'get_local_modules').", file=sys.stderr)
        print("  - Imports on the same line as magics (e.g., `%time import pandas`) will be missed.", file=sys.stderr)


if __name__ == "__main__":
    main()
