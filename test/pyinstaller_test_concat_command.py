# A simply python routine used to test the abilitlity to make an exedutable with pyinstaller
#
# Making this script an exedutable
# pip install pyinstaller
# pyinstaller --onefile pyinstaller_test_concat_command.py

import sys

def concatenate_files(input_file1, input_file2, output_file):
    with open(input_file1, 'r') as file1, open(input_file2, 'r') as file2, open(output_file, 'w') as outfile:
        # Read content from the first file
        content1 = file1.read()
        # Read content from the second file
        content2 = file2.read()
        # Write the concatenated content to the output file
        outfile.write(content1 + content2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <input_file1> <input_file2> <output_file>")
        sys.exit(1)
    
    input_file1 = sys.argv[1]
    input_file2 = sys.argv[2]
    output_file = sys.argv[3]

    concatenate_files(input_file1, input_file2, output_file)
