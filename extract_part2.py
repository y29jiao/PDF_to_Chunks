import os
import re
import json
import requests
import time
from bs4 import BeautifulSoup

def load_html_file(html_file):
    """Load HTML file"""
    with open(html_file, 'r', encoding='utf-8') as f:
        return f.read()

def extract_part2_content(html_content):
    """Extract Part 2 content from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all page divs
    pages = soup.find_all('div', class_='page')
    
    part2_content = []
    found_part2 = False
    part3_started = False
    
    # Iterate through all pages to find Part 2 start and end
    for page in pages:
        page_number = page.get('data-page-number', '')
        
        # Check if this is page 51 (start of Part 2)
        if page_number == '51':
            found_part2 = True
            print(f"Found start of Part 2 on page {page_number}")
        
        # Check if Part 3 has started (if it exists)
        if found_part2 and page.find('p', string=re.compile(r'Part 3')):
            part3_started = True
            print(f"Found start of Part 3 on page {page_number}")
            break
        
        # If Part 2 found and Part 3 not yet started, extract all text from this page
        if found_part2 and not part3_started:
            # Get all paragraph text from the page
            paragraphs = page.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if text and not text.startswith("National Building Code of Canada") and not text.startswith("Copyright ©"):
                    # Exclude headers and footers
                    if not (text.startswith("Division A") and len(text) < 15) and not re.match(r'^\d+-\d+\s+Division\s+A$', text):
                        part2_content.append(text)
    
    return part2_content

def process_part2_content(content):
    """Process Part 2 content, organize by section"""
    sections = []
    current_section = {"title": "Part 2 - Objectives", "content": []}
    
    for line in content:
        # Skip already added Part 2 title
        if line == "Part 2" or line == "Objectives":
            continue
            
        # Check if this is a new section title
        if re.match(r'^(2\.\d+\.?)$', line) or re.match(r'^Section\s+2\.\d+\.', line):
            # Save previous section
            if current_section["content"]:
                sections.append(current_section)
            
            # Create new section
            current_section = {"title": line, "content": []}
        # Check if this is a subsection title
        elif re.match(r'^(2\.\d+\.\d+\.?)$', line) or re.match(r'^(2\.\d+\.\d+\.\d+\.?)$', line):
            # Save previous subsection
            if current_section["content"]:
                sections.append(current_section)
            
            # Create new subsection
            current_section = {"title": line, "content": []}
        # If regular content, add to current section
        else:
            current_section["content"].append(line)
    
    # Add the last section
    if current_section["content"]:
        sections.append(current_section)
    
    return sections

def call_gpt_api(section_content, api_key):
    """Call GPT API to merge paragraphs"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt = f"""
Please merge the following text fragments into coherent paragraphs. These texts are from a building code document and might have been split into multiple lines due to PDF to HTML conversion.
Please maintain the original meaning and technical terminology, just fix the sentence breaks to make it complete and coherent paragraphs.

DO NOT translate the text. Keep it in its original English language.

Text content:
{json.dumps(section_content, ensure_ascii=False)}
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional text processing assistant responsible for merging fragmented text into coherent paragraphs. Always respond in English and do not translate the content."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        merged_text = result["choices"][0]["message"]["content"]
        return merged_text
    except Exception as e:
        print(f"API call error: {e}")
        if 'response' in locals():
            print(f"API response: {response.text}")
        # If API call fails, return simple merge of original content
        return " ".join(section_content)

def merge_sections_with_gpt(sections, api_key):
    """Use GPT to merge content for each section"""
    merged_sections = []
    
    for i, section in enumerate(sections):
        print(f"Processing section {i+1}/{len(sections)}: {section['title']}")
        
        # If section content is not empty, call GPT to merge
        if section["content"]:
            merged_content = call_gpt_api(section["content"], api_key)
            time.sleep(1)  # Avoid API rate limits
        else:
            merged_content = ""
        
        merged_sections.append({
            "title": section["title"],
            "content": merged_content
        })
    
    return merged_sections

def format_merged_content(merged_sections):
    """Format merged content"""
    formatted_content = ["Part 2", "Objectives", ""]
    
    for section in merged_sections:
        # Add section title
        formatted_content.append("\n" + section["title"])
        
        # Add section content
        if section["content"]:
            formatted_content.append(section["content"])
        
        # Add empty line separator
        formatted_content.append("")
    
    return formatted_content

def save_to_txt(content, output_file):
    """Save content to text file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in content:
            f.write(line + '\n')

def main():
    # Input and output file paths
    input_file = 'chunks/part_2_31_to_60.html'
    output_file = 'part2_content.txt'
    
    # OpenAI API key
    api_key = "YOUR_API_KEY_HERE"
    
    # Ensure input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
    
    # Load HTML file
    html_content = load_html_file(input_file)
    
    # Extract Part 2 content
    part2_content = extract_part2_content(html_content)
    
    if not part2_content:
        print("Warning: Could not find Part 2 content")
        return
    
    # Process content, organize by section
    sections = process_part2_content(part2_content)
    
    print(f"Identified {len(sections)} sections")
    
    # Use GPT to merge content for each section
    merged_sections = merge_sections_with_gpt(sections, api_key)
    
    # Format merged content
    formatted_content = format_merged_content(merged_sections)
    
    # Save extracted content
    save_to_txt(formatted_content, output_file)
    
    print(f"Successfully extracted and merged Part 2 content, saved to {output_file}")
    print(f"Processed {len(merged_sections)} sections")

if __name__ == "__main__":
    main() 