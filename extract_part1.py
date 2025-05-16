#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from bs4 import BeautifulSoup
import re
import argparse
from tqdm import tqdm
import requests
import time

def load_html_file(html_file):
    """Load HTML file"""
    with open(html_file, 'r', encoding='utf-8') as f:
        return f.read()

def is_article_number(text):
    """Check if text is an article number (e.g. 1.2.1.1, 1.2.3.4)"""
    # Match title patterns consisting of numbers and dots
    patterns = [
        r'^(\d+\.\d+\.\d+\.\d+)(\.)?$',  # Match 1.2.3.4 or 1.2.3.4. format
        r'^Article (\d+\.\d+\.\d+\.\d+)',  # Match Article 1.2.3.4 format
        r'^Section (\d+\.\d+\.\d+)',      # Match Section 1.2.3 format
        r'^(\d+\.\d+\.\d+\.\d+)(\.)?',    # Match 1.2.3.4 or 1.2.3.4. format, no space needed
        r'^(\d+\.\d+\.\d+)(\.)?',         # Match 1.2.3 or 1.2.3. format, no space needed
    ]
    
    for pattern in patterns:
        if re.match(pattern, text):
            return True
    return False

def extract_article_number(text):
    """Extract article number (e.g. '1.2.3.4') from text"""
    patterns = [
        r'(\d+\.\d+\.\d+\.\d+)',  # Match 1.2.3.4 format
        r'(\d+\.\d+\.\d+)',       # Match 1.2.3 format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def extract_content_from_html_files(html_files):
    """Extract content from multiple HTML files"""
    all_paragraphs = []
    
    for html_file in html_files:
        print(f"Processing file: {html_file}")
        html_content = load_html_file(html_file)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get all paragraphs
        paragraphs = soup.find_all('p')
        
        # Add to total list
        all_paragraphs.extend(paragraphs)
    
    return all_paragraphs

def find_part1_content(paragraphs):
    """Find Part 1 content"""
    part1_content = []
    
    # Try multiple methods to find Part 1 content
    # Method 1: Look for Division B and Part 1 markers
    start_index = None
    for i, p in enumerate(paragraphs):
        text = p.get_text().strip()
        
        # Look for Division B marker followed by Part 1 marker
        if "Division B" in text and "Part 1" in text:
            start_index = i
            print(f"Method 1: Found Division B and Part 1 marker: '{text}'")
            break
        
        # Look for standalone Part 1 marker
        if text.strip() == "Part 1" or text.strip() == "Part 1." or "Part 1 General" in text:
            start_index = i
            print(f"Method 1: Found standalone Part 1 marker: '{text}'")
            break
    
    # Method 2: Look for titles starting with "1.1"
    if start_index is None:
        for i, p in enumerate(paragraphs):
            text = p.get_text().strip()
            
            # Look for 1.1.1.1 format or Section 1.1.1 format
            if re.match(r'^1\.1(\.\d+)*\.?$', text) or "Section 1.1" in text:
                start_index = i
                print(f"Method 2: Found Part 1 numbering marker: '{text}'")
                break
    
    # Method 3: Look for specific titles like "Non-defined Terms" or "Defined Terms"
    if start_index is None:
        for i, p in enumerate(paragraphs):
            text = p.get_text().strip()
            
            if "Non-defined Terms" in text or "Defined Terms" in text:
                # Look back a few elements to find a suitable starting point
                for j in range(max(0, i-10), i):
                    prev_text = paragraphs[j].get_text().strip()
                    if re.match(r'^1\.2\.1\.\d+\.?$', prev_text):
                        start_index = j
                        print(f"Method 3: Found title marker near 'Terms': '{prev_text}'")
                        break
                if start_index:
                    break
    
    # If all methods fail, try to extract content from the beginning of the file
    if start_index is None:
        print("Warning: Could not find clear start of Part 1, will start from beginning of document")
        start_index = 0
    
    # Determine content end position
    end_index = None
    
    # Look for Part 2 or Division C marker
    for i in range(start_index + 1, len(paragraphs)):
        text = paragraphs[i].get_text().strip()
        
        if "Part 2" in text or "Division C" in text or text.startswith("2."):
            end_index = i
            print(f"Found Part 1 end marker: '{text}'")
            break
    
    # If no end marker is found, use the rest of the document
    if end_index is None:
        part1_paragraphs = paragraphs[start_index:]
        print("No Part 1 end marker found, using the rest of the document")
    else:
        part1_paragraphs = paragraphs[start_index:end_index]
    
    # Extract text content
    for p in part1_paragraphs:
        text = p.get_text().strip()
        if text:  # Skip empty text
            part1_content.append(text)
    
    print(f"Extracted {len(part1_content)} Part 1 content text blocks")
    
    # If extracted content is very small, try alternative method
    if len(part1_content) < 10:
        print("Warning: Extracted Part 1 content is too small, trying alternative method...")
        
        # Alternative method: Check all paragraphs, extract all that start with "1." and contain 1.x.x.x format and their subsequent content
        alternative_content = []
        in_part1 = False
        
        for p in paragraphs:
            text = p.get_text().strip()
            
            # Check if this is Part 1 content
            if re.match(r'^1\.\d+(\.\d+)*\.?', text) or (in_part1 and not text.startswith("2.")):
                in_part1 = True
                if text:  # Skip empty text
                    alternative_content.append(text)
            
            # Check if we've left Part 1 area
            if in_part1 and (text.startswith("2.") or "Part 2" in text or "Division C" in text):
                in_part1 = False
        
        # If alternative method extracted more content, use it
        if len(alternative_content) > len(part1_content):
            print(f"Alternative method extracted {len(alternative_content)} text blocks, using alternative result")
            part1_content = alternative_content
    
    return part1_content

def call_gpt4o_mini(text_chunks, api_key):
    """Call GPT-4o-mini API to identify paragraphs"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt = f"""
You are a paragraph restructuring expert. The following are text fragments from a PDF converted to HTML, where each line has been split into separate blocks due to PDF conversion issues.
Please analyze these text fragments and determine which ones should be merged into single paragraphs.

**Important rules:**
1. For title patterns like "1.2.3.4", "Article 1.2.3.4", "Section 1.2.3", these are standalone titles and should be separate paragraphs.
2. Each small title and its related content should be in different paragraphs. For example, content under 1.2.2.2 should be separate from content under 1.2.2.3.
3. If you see a format like "1.2.3.4 Something", this is typically the start of a title and should be separated from previous content.
4. Even within the same batch, if text blocks belong to different titles (e.g., 1.2.2.1 and 1.2.2.2), they should not be merged.
5. For numbered paragraphs (like 1), 2), a), b), etc.), each numbered item should be a separate paragraph, but their content may span multiple lines that need to be merged.

Return a standard JSON array where each element represents a paragraph, in the format:
[
  {{
    "paragraph_index": 0,
    "chunk_indices": [0, 1, 2]  // This indicates that text blocks 0, 1, and 2 should be merged into a single paragraph
  }},
  ...
]

Ensure your response can be parsed directly by json.loads() without any explanatory text or formatting characters. Return only the JSON array.

Here are the text blocks to analyze:
{json.dumps(text_chunks, ensure_ascii=False)}
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional text analysis assistant responsible for identifying text paragraph structure. Return only a valid JSON array without any explanatory text. Remember, content under different title numbers (like 1.2.2.1 and 1.2.2.2) must be processed separately and not merged into the same paragraph."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Try to extract JSON part (if API returned extra explanatory text)
        try:
            # Try direct parsing
            return json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON part from content
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # Try to extract part marked with ```json and ``` tags
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # All attempts failed, print detailed error info
            print(f"Could not parse API returned JSON: {content}")
            
            # If parsing fails, return a simple merge strategy: merge all blocks into one paragraph
            return [{"paragraph_index": 0, "chunk_indices": list(range(len(text_chunks)))}]
            
    except Exception as e:
        print(f"API call error: {e}")
        if 'response' in locals():
            print(f"API response: {response.text}")
        
        # If API call fails, return a simple merge strategy: merge all blocks into one paragraph
        return [{"paragraph_index": 0, "chunk_indices": list(range(len(text_chunks)))}]

def process_content(content):
    """Process content to identify sections and subsections"""
    sections = []
    current_section = None
    current_subsection = None
    current_text = []
    
    for line in content:
        # Check if this is a section title (e.g., "1.1")
        if re.match(r'^1\.\d+\.?$', line) or line.startswith("Section 1."):
            # Save previous section if exists
            if current_section is not None:
                # Add remaining text to the current subsection
                if current_text:
                    if current_subsection is None:
                        # If no subsection exists, add text directly to section
                        sections[-1]["content"].extend(current_text)
                    else:
                        # Add text to the current subsection
                        sections[-1]["subsections"][-1]["content"].extend(current_text)
                    current_text = []
            
            # Extract section number
            section_number = extract_article_number(line)
            
            # Create new section
            current_section = {
                "title": line,
                "number": section_number,
                "subsections": [],
                "content": []
            }
            sections.append(current_section)
            current_subsection = None
            
        # Check if this is a subsection title (e.g., "1.1.1")
        elif re.match(r'^1\.\d+\.\d+\.?$', line):
            # Add remaining text to the previous subsection if exists
            if current_text:
                if current_subsection is None:
                    # If no subsection exists, add text directly to section
                    if current_section is not None:
                        current_section["content"].extend(current_text)
                else:
                    # Add text to the current subsection
                    current_section["subsections"][-1]["content"].extend(current_text)
                current_text = []
            
            # Extract subsection number
            subsection_number = extract_article_number(line)
            
            # Create new subsection
            if current_section is not None:
                current_subsection = {
                    "title": line,
                    "number": subsection_number,
                    "content": []
                }
                current_section["subsections"].append(current_subsection)
            
        # Check if this is a sub-subsection title (e.g., "1.1.1.1")
        elif re.match(r'^1\.\d+\.\d+\.\d+\.?$', line):
            # Add remaining text to the previous section/subsection
            if current_text:
                if current_subsection is None:
                    # If no subsection exists, add text directly to section
                    if current_section is not None:
                        current_section["content"].extend(current_text)
                else:
                    # Add text to the current subsection
                    current_section["subsections"][-1]["content"].extend(current_text)
                current_text = []
            
            # For sub-subsections, we'll add them as content to the parent subsection
            if current_subsection is not None:
                current_subsection["content"].append(line)
            elif current_section is not None:
                current_section["content"].append(line)
            
        # Regular content
        else:
            current_text.append(line)
    
    # Add any remaining text
    if current_text:
        if current_subsection is None:
            # If no subsection exists, add text directly to section
            if current_section is not None:
                current_section["content"].extend(current_text)
        else:
            # Add text to the current subsection
            current_section["subsections"][-1]["content"].extend(current_text)
    
    return sections

def merge_paragraphs_in_sections(sections, api_key, batch_size=15):
    """Merge paragraphs within sections using GPT API"""
    merged_sections = []
    
    for section in sections:
        # Create a copy of the section
        merged_section = {
            "title": section["title"],
            "number": section["number"],
            "subsections": [],
            "content": []
        }
        
        # Merge content in the main section
        if section["content"]:
            # Split content into batches to avoid API limits
            for i in range(0, len(section["content"]), batch_size):
                batch = section["content"][i:i+batch_size]
                
                # Call API to get paragraph structure
                paragraph_structure = call_gpt4o_mini(batch, api_key)
                
                # Merge paragraphs according to API response
                for paragraph in paragraph_structure:
                    merged_paragraph = " ".join([batch[idx] for idx in paragraph["chunk_indices"]])
                    merged_section["content"].append(merged_paragraph)
                
                # Add delay to avoid rate limits
                time.sleep(1)
        
        # Process subsections
        for subsection in section["subsections"]:
            merged_subsection = {
                "title": subsection["title"],
                "number": subsection["number"],
                "content": []
            }
            
            # Merge content in the subsection
            if subsection["content"]:
                # Split content into batches to avoid API limits
                for i in range(0, len(subsection["content"]), batch_size):
                    batch = subsection["content"][i:i+batch_size]
                    
                    # Call API to get paragraph structure
                    paragraph_structure = call_gpt4o_mini(batch, api_key)
                    
                    # Merge paragraphs according to API response
                    for paragraph in paragraph_structure:
                        merged_paragraph = " ".join([batch[idx] for idx in paragraph["chunk_indices"]])
                        merged_subsection["content"].append(merged_paragraph)
                    
                    # Add delay to avoid rate limits
                    time.sleep(1)
            
            merged_section["subsections"].append(merged_subsection)
        
        merged_sections.append(merged_section)
    
    return merged_sections

def auto_merge_text_chunks(chunks):
    """Automatically merge text chunks without using API"""
    merged_paragraphs = []
    current_paragraph = []
    current_title = None
    
    for i, chunk in enumerate(chunks):
        # Check if this chunk is a title
        if is_article_number(chunk):
            # If we have accumulated text, save it as a paragraph
            if current_paragraph:
                merged_paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Save this title as a separate paragraph
            merged_paragraphs.append(chunk)
            current_title = extract_article_number(chunk)
            continue
        
        # Check if this chunk starts with a title pattern
        title_match = re.match(r'^(\d+\.\d+(\.\d+)*\.?)\s+(.+)$', chunk)
        if title_match:
            # If we have accumulated text, save it as a paragraph
            if current_paragraph:
                merged_paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Save this title+text as a separate paragraph
            merged_paragraphs.append(chunk)
            current_title = title_match.group(1)
            continue
        
        # Check if this is a numbered list item
        list_item_match = re.match(r'^(\d+\)|\w+\))\s+(.+)$', chunk)
        if list_item_match:
            # If we have accumulated text, save it as a paragraph
            if current_paragraph:
                merged_paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            
            # Start a new paragraph with this list item
            current_paragraph.append(chunk)
            continue
        
        # Check if this chunk ends with a sentence-ending punctuation
        if current_paragraph and current_paragraph[-1][-1] in ['.', '!', '?', ':', ';']:
            # If the previous chunk ended with punctuation, this might be a new paragraph
            # But we need to check if it's not a continuation (e.g., "e.g.", "i.e.", etc.)
            prev_ends_with_abbrev = re.search(r'(e\.g\.|i\.e\.|etc\.)$', current_paragraph[-1])
            if not prev_ends_with_abbrev:
                # If not an abbreviation, check if this chunk starts with a capital letter
                if chunk and chunk[0].isupper():
                    # Likely a new paragraph
                    merged_paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = [chunk]
                    continue
        
        # If none of the above conditions are met, add to current paragraph
        current_paragraph.append(chunk)
    
    # Add the last paragraph if it exists
    if current_paragraph:
        merged_paragraphs.append(" ".join(current_paragraph))
    
    return merged_paragraphs

def format_output(merged_sections):
    """Format merged sections for output"""
    output_lines = ["Part 1", ""]
    
    for section in merged_sections:
        # Add section title
        output_lines.append(section["title"])
        
        # Add section content
        for paragraph in section["content"]:
            output_lines.append(paragraph)
            output_lines.append("")  # Empty line after paragraph
        
        # Add subsections
        for subsection in section["subsections"]:
            # Add subsection title
            output_lines.append(subsection["title"])
            
            # Add subsection content
            for paragraph in subsection["content"]:
                output_lines.append(paragraph)
                output_lines.append("")  # Empty line after paragraph
    
    return output_lines

def save_to_txt(content, output_file):
    """Save content to text file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in content:
            f.write(line + '\n')

def save_to_json(sections, output_file):
    """Save sections to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Extract and process Part 1 content from HTML files")
    parser.add_argument("--html", nargs='+', default=["chunks/part_1_1_to_30.html"], 
                        help="Path to HTML files (default: chunks/part_1_1_to_30.html)")
    parser.add_argument("--output", default="part1_content.txt",
                        help="Output file path (default: part1_content.txt)")
    parser.add_argument("--json", default="part1_sections.json",
                        help="JSON output file path (default: part1_sections.json)")
    parser.add_argument("--api-key", default="YOUR_API_KEY_HERE",
                        help="OpenAI API key")
    parser.add_argument("--no-api", action="store_true",
                        help="Don't use API for paragraph merging")
    
    args = parser.parse_args()
    
    # Extract paragraphs from HTML files
    paragraphs = extract_content_from_html_files(args.html)
    
    # Find Part 1 content
    part1_content = find_part1_content(paragraphs)
    
    # Process content to identify sections
    sections = process_content(part1_content)
    
    # Merge paragraphs
    if args.no_api:
        print("Using automatic paragraph merging (no API)")
        # Apply simple automatic merging for each section and subsection
        merged_sections = []
        
        for section in sections:
            merged_section = {
                "title": section["title"],
                "number": section["number"],
                "subsections": [],
                "content": auto_merge_text_chunks(section["content"])
            }
            
            for subsection in section["subsections"]:
                merged_subsection = {
                    "title": subsection["title"],
                    "number": subsection["number"],
                    "content": auto_merge_text_chunks(subsection["content"])
                }
                merged_section["subsections"].append(merged_subsection)
            
            merged_sections.append(merged_section)
    else:
        print("Using API for paragraph merging")
        merged_sections = merge_paragraphs_in_sections(sections, args.api_key)
    
    # Format output
    output_content = format_output(merged_sections)
    
    # Save to files
    save_to_txt(output_content, args.output)
    save_to_json(merged_sections, args.json)
    
    print(f"Part 1 content extracted and saved to {args.output}")
    print(f"Section structure saved to {args.json}")

if __name__ == "__main__":
    main() 