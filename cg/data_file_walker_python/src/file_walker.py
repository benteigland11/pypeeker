import os

def walk_python_files(root_dir, ignore_dirs=None):
    """
    Recursively find all .py files in a directory.
    :param root_dir: The directory to start searching from.
    :param ignore_dirs: A list of directory names to ignore (e.g., ['.git', 'venv']).
    :return: A list of absolute file paths.
    """
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules'}
    else:
        ignore_dirs = set(ignore_dirs)

    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories in-place to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.abspath(os.path.join(root, file)))
    
    return python_files
