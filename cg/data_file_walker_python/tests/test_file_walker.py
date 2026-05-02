from src.file_walker import walk_python_files
import os
import shutil
import tempfile

def test_walk_python_files():
    temp_dir = tempfile.mkdtemp()
    try:
        open(os.path.join(temp_dir, "test1.py"), "w").close()
        os.mkdir(os.path.join(temp_dir, "subdir"))
        open(os.path.join(temp_dir, "subdir", "test2.py"), "w").close()
        open(os.path.join(temp_dir, "subdir", "ignore.txt"), "w").close()
        
        files = walk_python_files(temp_dir)
        assert len(files) == 2
        # Use abspath for comparison
        expected = {os.path.abspath(os.path.join(temp_dir, "test1.py")), 
                    os.path.abspath(os.path.join(temp_dir, "subdir", "test2.py"))}
        assert set(files) == expected
    finally:
        shutil.rmtree(temp_dir)
