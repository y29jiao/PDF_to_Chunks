#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Conversion Tool - Convert PDF files to HTML or plain text format

This script converts PDF documents to HTML or plain text format while intelligently preserving 
the original paragraph structure of the PDF.

Main features:
1. Convert PDF to a single HTML file
2. Convert PDF to multiple HTML files (each containing several pages)
3. Convert PDF to plain text format

Paragraph preservation:
When using the --preserve-paragraphs parameter, the script analyzes the PDF page layout,
identifying paragraph boundaries by recognizing line spacing, indentation, and punctuation.
This is particularly useful for text-rich PDF documents like papers, books, and articles.

Usage examples:
1. Convert PDF to a single HTML file, preserving paragraph structure:
   python pdf_convert.py input.pdf -o output.html --preserve-paragraphs

2. Convert PDF to plain text:
   python pdf_convert.py input.pdf -f text -o output.txt 

3. Split large PDF into multiple HTML files, each containing 50 pages:
   python pdf_convert.py large_file.pdf -f html-chunks -c output_directory -p 50

Advanced paragraph control:
--para-gap-factor: Adjusts the line spacing threshold, higher values make it less likely to detect new paragraphs
--para-indent-threshold: Adjusts the indentation threshold (pixels), higher values make it less likely to detect new paragraphs based on indentation
"""

import fitz  # PyMuPDF
import os
import re
import argparse
from tqdm import tqdm
import html
import gc
import sys

class PDFConverter:
    def __init__(self, pdf_path):
        """Initialize PDF converter
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        # Don't open document during initialization, defer until needed
        self.doc = None
        self.total_pages = 0
    
    def _open_document(self):
        """Open PDF document on demand"""
        if self.doc is None:
            self.doc = fitz.open(self.pdf_path)
            self.total_pages = self.doc.page_count
            print(f"Opened PDF file: {self.pdf_path}, total pages: {self.total_pages}")
            # Force garbage collection
            gc.collect()
        return self.doc
    
    def _close_document(self):
        """Close PDF document and release resources"""
        if self.doc:
            self.doc.close()
            self.doc = None
            gc.collect()
            print("PDF document closed")
    
    def _extract_page_text_simple(self, page_num, include_html_tags=True, preserve_paragraphs=False, 
                               para_gap_factor=1.5, para_indent_threshold=10):
        """Extract text from a single page with minimal memory usage
        
        Args:
            page_num: Page number (0-based)
            include_html_tags: Whether to include HTML tags
            preserve_paragraphs: Whether to preserve original paragraph structure
            para_gap_factor: When line spacing exceeds line height by this factor, consider it a new paragraph
            para_indent_threshold: When line indentation exceeds this pixel value, consider it a new paragraph
            
        Returns:
            Page text content
        """
        try:
            doc = self._open_document()
            page = doc[page_num]
            
            if include_html_tags:
                if preserve_paragraphs:
                    # Use advanced paragraph processing
                    # Get structured info in dict format, but set flags=0 to exclude images to reduce memory usage
                    text = page.get_text("dict", flags=0)
                    processed_text = f'<div class="page" id="page_{page_num+1}" data-page-number="{page_num+1}">\n'
                    
                    # Process each text block, preserving paragraph structure
                    for block in text["blocks"]:
                        if block["type"] == 0:  # Text block
                            para_text = []
                            prev_y1 = -1
                            para_start = True
                            
                            for line in block["lines"]:
                                line_text = ""
                                for span in line["spans"]:
                                    line_text += span["text"]
                                
                                line_text = line_text.strip()
                                if not line_text:
                                    continue  # Skip empty lines
                                    
                                # Check if this is the start of a new paragraph
                                if not para_start and prev_y1 > 0:
                                    y_gap = line["bbox"][1] - prev_y1
                                    line_height = line["bbox"][3] - line["bbox"][1]
                                    x_indent = line["bbox"][0] - block["lines"][0]["bbox"][0]
                                    
                                    # Determine if this is a new paragraph:
                                    # 1. Line spacing > para_gap_factor * line height, or
                                    # 2. Significant indentation (> para_indent_threshold), or
                                    # 3. Previous line ends with period, question mark, exclamation mark, etc.
                                    new_para = (
                                        (y_gap > para_gap_factor * line_height) or 
                                        (x_indent > para_indent_threshold) or
                                        (len(para_text) > 0 and para_text[-1] and 
                                         para_text[-1][-1] in ['.', '?', '!', ':', ';'])
                                    )
                                else:
                                    new_para = False
                                    
                                if new_para and para_text:
                                    # End previous paragraph and start a new one
                                    processed_text += f'<p>{html.escape(" ".join(para_text))}</p>\n'
                                    para_text = [line_text]
                                else:
                                    # Continue current paragraph
                                    if para_text:
                                        if line_text.endswith("-"):
                                            # If ending with hyphen, merge words (remove hyphen)
                                            para_text.append(line_text[:-1])
                                        else:
                                            # If not ending with hyphen, add space
                                            para_text.append(line_text)
                                    else:
                                        para_text.append(line_text)
                                
                                prev_y1 = line["bbox"][3]
                                para_start = False
                                
                                # Process line by line to avoid memory accumulation
                                if len(para_text) > 100:  # If paragraph is too long, force split
                                    processed_text += f'<p>{html.escape(" ".join(para_text))}</p>\n'
                                    para_text = []
                            
                            # Process the last paragraph
                            if para_text:
                                processed_text += f'<p>{html.escape(" ".join(para_text))}</p>\n'
                        
                        elif block["type"] == 1:  # Image block
                            # Add placeholder for images
                            processed_text += f'<div class="image">[Image]</div>\n'
                    
                    processed_text += '</div>\n'
                else:
                    # Use simple line-by-line approach
                    text = page.get_text("text")
                    processed_text = f'<div class="page" id="page_{page_num+1}" data-page-number="{page_num+1}">\n'
                    
                    # Simple text processing, wrap each paragraph in <p> tags
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():  # Skip empty lines
                            processed_text += f'<p>{html.escape(line)}</p>\n'
                    
                    processed_text += '</div>\n'
                
                # Help garbage collection
                page = None
                text = None
                gc.collect()
                
                return processed_text
            else:
                # Return plain text only
                if preserve_paragraphs:
                    # Process with paragraph structure preservation
                    # Set flags=0 to exclude image content to reduce memory usage
                    text_dict = page.get_text("dict", flags=0)
                    text_lines = []
                    
                    # Process block by block to avoid memory accumulation
                    for block in text_dict["blocks"]:
                        if block["type"] == 0:  # Text block
                            para_text = []
                            prev_y1 = -1
                            para_start = True
                            
                            for line in block["lines"]:
                                line_text = ""
                                for span in line["spans"]:
                                    line_text += span["text"]
                                
                                line_text = line_text.strip()
                                if not line_text:
                                    continue  # Skip empty lines
                                    
                                # Check if this is a new paragraph
                                if not para_start and prev_y1 > 0:
                                    y_gap = line["bbox"][1] - prev_y1
                                    line_height = line["bbox"][3] - line["bbox"][1]
                                    x_indent = line["bbox"][0] - block["lines"][0]["bbox"][0]
                                    
                                    # Same paragraph detection logic as in HTML version
                                    new_para = (
                                        (y_gap > para_gap_factor * line_height) or 
                                        (x_indent > para_indent_threshold) or
                                        (len(para_text) > 0 and para_text[-1] and 
                                         para_text[-1][-1] in ['.', '?', '!', ':', ';'])
                                    )
                                else:
                                    new_para = False
                                    
                                if new_para and para_text:
                                    # End paragraph with double line break
                                    text_lines.append(" ".join(para_text))
                                    text_lines.append("")  # Empty line indicates paragraph separation
                                    para_text = [line_text]
                                else:
                                    # Continue current paragraph
                                    if para_text:
                                        if line_text.endswith("-"):
                                            para_text.append(line_text[:-1])
                                        else:
                                            para_text.append(line_text)
                                    else:
                                        para_text.append(line_text)
                                
                                prev_y1 = line["bbox"][3]
                                para_start = False
                                
                                # If paragraph is too long, force split to avoid memory accumulation
                                if len(para_text) > 100:
                                    text_lines.append(" ".join(para_text))
                                    para_text = []
                            
                            # Process last line of paragraph
                            if para_text:
                                text_lines.append(" ".join(para_text))
                        
                        elif block["type"] == 1:  # Image block
                            # Add placeholder for images
                            text_lines.append("[Image]")
                            text_lines.append("")  # Empty line after image
                    
                    # Help garbage collection
                    page = None
                    text_dict = None
                    gc.collect()
                    
                    return "\n".join(text_lines)
                else:
                    # Simple text extraction without paragraph preservation
                    text = page.get_text("text")
                    
                    # Help garbage collection
                    page = None
                    gc.collect()
                    
                    return text
        except Exception as e:
            print(f"Error extracting text from page {page_num}: {e}")
            return ""
    
    def convert_to_html_chunks(self, output_dir, chunk_size=10, pages_per_chunk=100, 
                             preserve_paragraphs=False, para_gap_factor=1.5, para_indent_threshold=10):
        """Convert PDF to multiple HTML files (chunks)
        
        Args:
            output_dir: Directory to save HTML chunks
            chunk_size: Number of pages to process at once (memory control)
            pages_per_chunk: Number of pages per output HTML file
            preserve_paragraphs: Whether to preserve paragraph structure
            para_gap_factor: Line spacing threshold factor
            para_indent_threshold: Indentation threshold in pixels
        
        Returns:
            List of created HTML files
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Open document
        doc = self._open_document()
        total_pages = self.total_pages
        
        # Calculate number of chunks
        num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
        created_files = []
        
        for chunk_idx in range(num_chunks):
            start_page = chunk_idx * pages_per_chunk
            end_page = min(start_page + pages_per_chunk, total_pages)
            
            chunk_file = os.path.join(output_dir, f"part_{chunk_idx+1}_{start_page+1}_to_{end_page}.html")
            created_files.append(chunk_file)
            
            print(f"Processing chunk {chunk_idx+1}/{num_chunks}: pages {start_page+1}-{end_page}")
            
            with open(chunk_file, 'w', encoding='utf-8') as f:
                # Write HTML header
                f.write('<!DOCTYPE html>\n<html>\n<head>\n')
                f.write('<meta charset="UTF-8">\n')
                f.write(f'<title>PDF Chunk {chunk_idx+1}: Pages {start_page+1}-{end_page}</title>\n')
                f.write('<style>\n')
                f.write('.page { margin-bottom: 20px; border-bottom: 1px dashed #ccc; padding-bottom: 10px; }\n')
                f.write('</style>\n')
                f.write('</head>\n<body>\n')
                
                # Process pages in smaller chunks to control memory usage
                for i in range(start_page, end_page, chunk_size):
                    sub_end = min(i + chunk_size, end_page)
                    
                    for page_num in tqdm(range(i, sub_end), desc=f"Pages {i+1}-{sub_end}"):
                        page_html = self._extract_page_text_simple(
                            page_num, 
                            include_html_tags=True,
                            preserve_paragraphs=preserve_paragraphs,
                            para_gap_factor=para_gap_factor,
                            para_indent_threshold=para_indent_threshold
                        )
                        f.write(page_html)
                        f.flush()  # Ensure data is written to disk
                    
                    # Force garbage collection after each sub-chunk
                    gc.collect()
                
                # Write HTML footer
                f.write('</body>\n</html>')
        
        # Close document
        self._close_document()
        
        return created_files
    
    def convert_to_html(self, output_path, chunk_size=5, 
                        preserve_paragraphs=False, para_gap_factor=1.5, para_indent_threshold=10):
        """Convert PDF to a single HTML file
        
        Args:
            output_path: Path to save the HTML file
            chunk_size: Number of pages to process at once (memory control)
            preserve_paragraphs: Whether to preserve paragraph structure
            para_gap_factor: Line spacing threshold factor
            para_indent_threshold: Indentation threshold in pixels
        
        Returns:
            Path to the created HTML file
        """
        # Open document
        doc = self._open_document()
        total_pages = self.total_pages
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write HTML header
            f.write('<!DOCTYPE html>\n<html>\n<head>\n')
            f.write('<meta charset="UTF-8">\n')
            f.write(f'<title>PDF Conversion</title>\n')
            f.write('<style>\n')
            f.write('.page { margin-bottom: 20px; border-bottom: 1px dashed #ccc; padding-bottom: 10px; }\n')
            f.write('</style>\n')
            f.write('</head>\n<body>\n')
            
            # Process pages in chunks to control memory usage
            for i in range(0, total_pages, chunk_size):
                end = min(i + chunk_size, total_pages)
                
                for page_num in tqdm(range(i, end), desc=f"Pages {i+1}-{end}"):
                    page_html = self._extract_page_text_simple(
                        page_num, 
                        include_html_tags=True,
                        preserve_paragraphs=preserve_paragraphs,
                        para_gap_factor=para_gap_factor,
                        para_indent_threshold=para_indent_threshold
                    )
                    f.write(page_html)
                    f.flush()  # Ensure data is written to disk
                
                # Force garbage collection after each chunk
                gc.collect()
            
            # Write HTML footer
            f.write('</body>\n</html>')
        
        # Close document
        self._close_document()
        
        return output_path
    
    def convert_to_text(self, output_path, chunk_size=10, 
                        preserve_paragraphs=False, para_gap_factor=1.5, para_indent_threshold=10):
        """Convert PDF to plain text
        
        Args:
            output_path: Path to save the text file
            chunk_size: Number of pages to process at once (memory control)
            preserve_paragraphs: Whether to preserve paragraph structure
            para_gap_factor: Line spacing threshold factor
            para_indent_threshold: Indentation threshold in pixels
        
        Returns:
            Path to the created text file
        """
        # Open document
        doc = self._open_document()
        total_pages = self.total_pages
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Process pages in chunks to control memory usage
            for i in range(0, total_pages, chunk_size):
                end = min(i + chunk_size, total_pages)
                
                for page_num in tqdm(range(i, end), desc=f"Pages {i+1}-{end}"):
                    page_text = self._extract_page_text_simple(
                        page_num, 
                        include_html_tags=False,
                        preserve_paragraphs=preserve_paragraphs,
                        para_gap_factor=para_gap_factor,
                        para_indent_threshold=para_indent_threshold
                    )
                    f.write(page_text)
                    f.write("\n\n--- Page Break ---\n\n")  # Add page break marker
                    f.flush()  # Ensure data is written to disk
                
                # Force garbage collection after each chunk
                gc.collect()
        
        # Close document
        self._close_document()
        
        return output_path
    
    def close(self):
        """Close the PDF document and release resources"""
        self._close_document()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert PDF to HTML or text with paragraph preservation')
    parser.add_argument('pdf_file', help='Path to the PDF file')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--format', choices=['html', 'text', 'html-chunks'], default='html',
                        help='Output format: html (default), text, or html-chunks')
    parser.add_argument('-c', '--chunks-dir', help='Directory to save HTML chunks (for html-chunks format)')
    parser.add_argument('-p', '--pages-per-chunk', type=int, default=50,
                        help='Number of pages per HTML chunk (for html-chunks format)')
    parser.add_argument('--preserve-paragraphs', action='store_true',
                        help='Preserve paragraph structure from PDF')
    parser.add_argument('--para-gap-factor', type=float, default=1.5,
                        help='Line spacing threshold factor for paragraph detection')
    parser.add_argument('--para-indent-threshold', type=int, default=10,
                        help='Indentation threshold (pixels) for paragraph detection')
    parser.add_argument('--chunk-size', type=int, default=10,
                        help='Number of pages to process at once (memory control)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.format != 'html-chunks' and not args.output:
        parser.error("--output is required for html and text formats")
    
    if args.format == 'html-chunks' and not args.chunks_dir:
        parser.error("--chunks-dir is required for html-chunks format")
    
    # Create converter
    converter = PDFConverter(args.pdf_file)
    
    try:
        # Convert based on format
        if args.format == 'html':
            output_file = converter.convert_to_html(
                args.output,
                chunk_size=args.chunk_size,
                preserve_paragraphs=args.preserve_paragraphs,
                para_gap_factor=args.para_gap_factor,
                para_indent_threshold=args.para_indent_threshold
            )
            print(f"PDF converted to HTML: {output_file}")
            
        elif args.format == 'text':
            output_file = converter.convert_to_text(
                args.output,
                chunk_size=args.chunk_size,
                preserve_paragraphs=args.preserve_paragraphs,
                para_gap_factor=args.para_gap_factor,
                para_indent_threshold=args.para_indent_threshold
            )
            print(f"PDF converted to text: {output_file}")
            
        elif args.format == 'html-chunks':
            output_files = converter.convert_to_html_chunks(
                args.chunks_dir,
                chunk_size=args.chunk_size,
                pages_per_chunk=args.pages_per_chunk,
                preserve_paragraphs=args.preserve_paragraphs,
                para_gap_factor=args.para_gap_factor,
                para_indent_threshold=args.para_indent_threshold
            )
            print(f"PDF converted to {len(output_files)} HTML chunks in: {args.chunks_dir}")
    
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)
    
    finally:
        # Ensure resources are released
        converter.close()

if __name__ == "__main__":
    main() 