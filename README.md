# PDF Content Extraction Tool

This tool extracts and organizes content from PDF documents based on their structure, breaking them down into volumes, parts, chapters, and sections, and saving the organized content in JSON format. The process is divided into multiple stages to improve efficiency and accuracy when handling large PDF files.

## Features

- Two-stage processing workflow for efficient and accurate handling of large PDF files
- Stage 1: Convert PDF to HTML format (supports single HTML file or chunked HTML files)
- Stage 2: Extract specific parts from HTML files based on document structure
- Process large documents efficiently
- Support for multi-level structure: Volumes, Parts, Sections, and Subsections
- Memory usage control to prevent program crashes
- Automatic filtering of images and tables to extract only relevant text content

## Installation

Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage Guide

### Step 1: Convert PDF to HTML

First, use `pdf_convert.py` to convert your PDF document to HTML format:

```
# Convert PDF to a single HTML file
python pdf_convert.py input.pdf -o output.html --preserve-paragraphs

# Convert PDF to multiple HTML chunks (recommended for large files)
python pdf_convert.py input.pdf -f html-chunks -c chunks_directory -p 50
```

This will create HTML files that preserve the original document structure. It's recommended to save as multiple HTML files for easier subsequent processing.

### Step 2: Extract Content

After converting to HTML, use either `extract_part1.py` or `extract_part2.py` to extract specific parts:

```
# Extract Part 1 content
python extract_part1.py --html chunks/part_1_1_to_30.html --output part1_content.txt

# Extract Part 2 content
python extract_part2.py
```

### Difference between extract_part1.py and extract_part2.py

- **extract_part1.py**: Extracts content from Part 1 of the document. It has more sophisticated section detection and can handle complex nested structures. It identifies sections, subsections, and sub-subsections, organizing them hierarchically in the output.

- **extract_part2.py**: Extracts content from Part 2 of the document. It has a simpler structure detection focused on the specific format of Part 2. It processes sections sequentially without the nested hierarchical structure of Part 1.

Both files use a similar approach: first identifying sections using hardcoded patterns, then using gpt-4o-mini to merge scattered sentences into coherent paragraphs to ensure readability of the output.

## Important Notes

1. **Path Configuration**: Before running the scripts, you need to modify the file paths in both extraction scripts to match your directory structure:
   - In `extract_part1.py`: Update the default HTML path in the `--html` argument
   - In `extract_part2.py`: Update the `input_file` and `output_file` variables

2. **API Key**: Both extraction scripts use OpenAI's API to improve paragraph detection. You need to:
   - Replace `YOUR_API_KEY_HERE` with your actual OpenAI API key
   - Or use the `--no-api` flag with `extract_part1.py` to use automatic paragraph detection without API

## Example Workflow

1. Convert a large PDF to HTML chunks:
   ```
   python pdf_convert.py large_document.pdf -f html-chunks -c chunks -p 50
   ```

2. Extract Part 1 content:
   ```
   python extract_part1.py --html chunks/part_1_1_to_30.html --output part1_content.txt
   ```

3. Extract Part 2 content (after updating the paths in the script):
   ```
   python extract_part2.py
   ```