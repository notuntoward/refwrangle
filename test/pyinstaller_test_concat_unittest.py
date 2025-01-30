# Tests 

import unittest
import tempfile
import os
import subprocess

scriptNm = "pyinstaller_test_concat_unittest"

class TestConcatenateFiles(unittest.TestCase):

    def setUp(self):
        # Create temporary files for testing
        self.temp_file1 = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file2 = tempfile.NamedTemporaryFile(delete=False)
        self.output_file = tempfile.NamedTemporaryFile(delete=False)

        # Write sample data to the first input file
        self.temp_file1.write(b"Hello, ")
        self.temp_file1.close()

        # Write sample data to the second input file
        self.temp_file2.write(b"World!")
        self.temp_file2.close()

    def tearDown(self):
        # Remove temporary files after test
        os.unlink(self.temp_file1.name)
        os.unlink(self.temp_file2.name)
        os.unlink(self.output_file.name)

    def test_concatenate_files(self):
        # Test the uncompiled script with the temporary files as arguments
        subprocess.run(['python', f'{scriptFNm}.py', self.temp_file1.name, self.temp_file2.name, self.output_file.name])

        # Read the output file and check its content
        with open(self.output_file.name, 'r') as f:
            result = f.read()
        
        expected_result = "Hello, World!"
        self.assertEqual(result, expected_result)

if __name__ == '__main__':
    unittest.main()
