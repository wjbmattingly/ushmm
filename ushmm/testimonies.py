import os
from pdf2image import convert_from_path
from typing import List
from typing import Optional
from PIL import Image
import pytesseract

from unidecode import unidecode
import re

import cv2
import numpy as np

from typing import List

def process_testimony_texts(input_directory: str, output_file: Optional[str] = None, save: bool = False) -> str:
    merged_text = ''
    for filename in sorted(os.listdir(input_directory)):
        if filename.endswith(".txt"):
            with open(os.path.join(input_directory, filename), 'r', encoding='utf-8') as file:
                if "0002" not in filename and "0001" not in filename:
                    merged_text += file.read() + " PAGE_BREAK "

    # Removing line breaks that are not supposed to split paragraphs
    merged_text = re.sub(r'(?<=[^\.!?])\n(?=[^\n])', ' ', merged_text)
    # Then, split into paragraphs at remaining line breaks
    paragraphs = merged_text.split('\n')

    # Beginning of the HTML document
    html_text = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>Document</title>\n</head>\n<body>'
    
    dialogue_block = ''
    current_dialogue_type = None
    page_counter = -1  # Set to -1 as it will be incremented on the first page break
    
    for paragraph in paragraphs:
        if 'PAGE_BREAK' in paragraph:
            page_counter += 1
            paragraph = paragraph.replace('PAGE_BREAK', f'<span class="page-break" number="{page_counter}"></span>')
        
        new_dialogue_type = 'Question' if paragraph.strip().startswith('Q:') else 'Answer'
        
        if new_dialogue_type != current_dialogue_type and dialogue_block:
            # Close previous dialogue block and open a new one
            html_text += f'<dialogue class="{current_dialogue_type}">{dialogue_block}</dialogue>\n'
            dialogue_block = ''
        
        dialogue_block += f'<p>{paragraph}</p>'
        current_dialogue_type = new_dialogue_type
    
    # Handling the last dialogue block
    if dialogue_block:
        html_text += f'<dialogue class="{current_dialogue_type}">{dialogue_block}</dialogue>\n'
        
    # Closing HTML tags
    html_text += '</body>\n</html>'
    
    if save and output_file:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            out_file.write(html_text)

    return html_text

def remove_footers(input_directory: str, output_directory: str = None, save: bool = False):
    # If the output_directory is provided, create it if it does not exist
    if output_directory and not os.path.exists(output_directory):
        os.makedirs(output_directory)
    # Initialize list to hold processed images
    processed_images = []
    # Iterate through all files in the input directory
    for filename in sorted(os.listdir(input_directory)):
        # Check if file is an image (you might need to check for other image file extensions)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):  
            image_path = os.path.join(input_directory, filename)
            
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Unable to load image at path: {image_path}")
                continue
            
            # Convert image to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Set a threshold to separate object and background
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    
            # Find contours in the thresholded image
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Initialize variable to hold the largest found contour
            largest_contour = None
            largest_contour_width = 0
    
            # Iterate over all found contours
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if h <= 2 and w > largest_contour_width and w > 40:  
                    largest_contour = contour
                    largest_contour_width = w
    
            # If a contour is found, crop the image above this contour
            if largest_contour is not None:
                x, y, w, h = cv2.boundingRect(largest_contour)
                print(f"Footer Found at {y}. Cropping Image")
                cropped_image = image[:y, :]
            else:
                # If no contour is found, use the original image
                cropped_image = image

            # Append the processed image to the list
            processed_images.append(cropped_image)

            # If save is True and output_directory is provided, save the image to the output directory
            if save and output_directory:
                output_path = os.path.join(output_directory, filename)
                cv2.imwrite(output_path, cropped_image)
                print(f"Processed image saved at: {output_path}")

    # Return the list of processed images
    return processed_images


def pdf_to_images(pdf_path: str, output_folder: str = None, save: bool = False) -> List[Image.Image]:
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} does not exist")
        return []
    
    if not output_folder:
        print("Error: Output folder must be specified")
        return []

    try:
        images = convert_from_path(pdf_path)
        if save:
            os.makedirs(output_folder, exist_ok=True)
            for i, image in enumerate(images, start=1):
                filename = f"{str(i).zfill(4)}.jpg"
                image_path = os.path.join(output_folder, filename)
                image.save(image_path, "JPEG")
                print(f"Saved: {image_path}")

        return images
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def images_to_text(img_dir: str, save: bool = False, output_folder: str = None) -> List[str]:
    # Check if the img_dir is valid
    if not os.path.exists(img_dir):
        print(f"Error: {img_dir} does not exist")
        return []
    
    # Get list of image files in img_dir
    img_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
    if not img_files:
        print(f"Error: No image files found in {img_dir}")
        return []
    img_files.sort()
    # Process each image
    texts = []
    for img_file in img_files:
        # Open image
        img_path = os.path.join(img_dir, img_file)
        img = Image.open(img_path)
        
        # OCR: Convert image to text
        text = pytesseract.image_to_string(img, config="--psm 6")
        texts.append(text)
        
        # Save text to file if save is True
        if save:
            if not output_folder:
                print("Error: Output folder must be specified when save is True")
                return []
            
            # Create output folder if it doesn't exist
            os.makedirs(output_folder, exist_ok=True)
            
            # Create text file path
            txt_file_path = os.path.join(output_folder, f"{os.path.splitext(img_file)[0]}.txt")
            
            # Write text to file
            with open(txt_file_path, 'w', encoding="utf-8") as txt_file:
                txt_file.write(text)
                print(f"Saved: {txt_file_path}")
            img.close()

    return texts

def normalize_page_content(text: str) -> str:
    """
    Normalize the page content by replacing variations of 'Question' and 'Answer' 
    with 'Q:' and 'A:' respectively.

    Parameters:
    text (str): The text content of the page to be normalized.

    Returns:
    str: The normalized text.
    """
    text = re.sub(r'(?i)question:', 'Q:', text)
    text = re.sub(r'(?i)answer:', 'A:', text)
    return text


from unidecode import unidecode
import re

def normalize_page_content(text: str) -> str:
    """
    Normalize the page content by replacing variations of 'Question' and 'Answer' 
    with 'Q:' and 'A:' respectively.

    Parameters:
    text (str): The text content of the page to be normalized.

    Returns:
    str: The normalized text.
    """
    text = re.sub(r'(?i)question:', 'Q:', text)
    text = re.sub(r'(?i)answer:', 'A:', text)
    return text

def remove_headers(text: str) -> str:
    """
    Flags and removes headers from the text.

    Parameters:
    text (str): The text content from which headers need to be removed.

    Returns:
    str: The text without headers.
    """
    # Define the header pattern
    header_pattern = re.compile(r'USHMM Archives RG-\d{2}\.\d{3}\*\d{4} \d', re.IGNORECASE)

    # Find all headers in the text
    headers = header_pattern.findall(text)
    
    # Flag (print) the headers
    for header in set(headers):
        print(f"Header Found: {header}")
    
    # Remove the headers from the text
    cleaned_text = header_pattern.sub('', text)

    return cleaned_text


def remove_timestamps(text: str) -> str:
    """
    Flags and removes timestamps from the text.

    Parameters:
    text (str): The text content from which timestamps need to be removed.

    Returns:
    str: The text without timestamps.
    """
    # Define the timestamp pattern (HH:MM:SS format)
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')
    
    # Find all timestamps in the text
    timestamps = timestamp_pattern.findall(text)
    
    # Flag (print) the timestamps
    for timestamp in set(timestamps):
        print(f"Timestamp Found: {timestamp}")
    
    # Remove the timestamps from the text
    cleaned_text = timestamp_pattern.sub('', text)

    return cleaned_text.strip()


def normalize_line_breaks(text: str, verbose: bool = True) -> str:
    """
    Normalizes consecutive line breaks in the text, converting any instance of more
    than two line breaks into exactly two.

    Parameters:
    text (str): The text content to be normalized.
    verbose (bool): If True, informs about the normalization process.

    Returns:
    str: The text with normalized line breaks.
    """
    # Define a pattern to match more than two consecutive line breaks
    line_break_pattern = re.compile(r'\n{3,}')
    
    # Find all matches of more than two consecutive line breaks
    excessive_breaks = line_break_pattern.findall(text)
    
    # Replace each match with exactly two line breaks
    normalized_text = line_break_pattern.sub('\n\n', text)

    if verbose and excessive_breaks:
        print(f"Normalized {len(excessive_breaks)} instances of excessive line breaks.")

    return normalized_text

def normalize_characters(text: str, verbose: bool = True) -> str:
    """
    Normalizes text by removing all diacritics, accent marks, etc. and converting them
    into standard English characters. It also handles Polish characters.

    Parameters:
    text (str): The text content to be normalized.
    verbose (bool): If True, prints each character that was changed.

    Returns:
    str: The normalized text.
    """
    exceptions = {"°", "o", ""}
    if verbose==True:
        print("Normalizing characters...")
    normalized_chars = []
    
    if verbose:
        for orig_char in text:
            norm_char = unidecode(orig_char)
            if orig_char != norm_char:
                print(f"Changed: {orig_char} -> {norm_char}")
            normalized_chars.append(norm_char)
        normalized_text = ''.join(normalized_chars)
    else:
        normalized_text = unidecode(text)
    
    return normalized_text

def normalize_quotes(text: str, verbose: bool = True) -> str:
    """
    Normalizes all quotations in the text to double quotation marks while ignoring contractions.

    Parameters:
    text (str): The text content to be normalized.
    verbose (bool): If True, prints each character that was changed.

    Returns:
    str: The text with normalized quotations.
    """
    if verbose==True:
        print("Normalizing quotes...")

    # First, find and store all contractions positions
    contraction_positions = [m.span() for m in re.finditer(r"\w'\w", text)]

    # Function to check if a given position is within a contraction
    def in_contraction(pos):
        return any(start <= pos <= end for start, end in contraction_positions)

    # List to hold characters of the new string
    new_chars = []

    # Iterate over characters and their positions in the text
    for i, char in enumerate(text):
        # If a single quote is not within a contraction, replace it
        if char == "'" and not in_contraction(i):
            new_char = '"'
            if verbose:
                print(f"Changed: {char} -> {new_char}")
        else:
            new_char = char  # Otherwise, keep the original character
        new_chars.append(new_char)

    # Join the characters to form the new string
    normalized_text = ''.join(new_chars)

    return normalized_text

def clean_texts(input_directory: str, save: bool = False, output_directory: str = None):
    """
    Processes all .txt files in the input directory with the normalization functions.

    Parameters:
    input_directory (str): The directory containing the .txt files to be processed.
    save (bool): If True, saves the processed texts to the output directory.
    output_directory (str): The directory to save processed texts, if save is True.
    """
    # Check if output_directory is provided when save is True
    if save and output_directory is None:
        raise ValueError("Output directory must be provided if save is True.")

    # Create output directory if it doesn't exist
    if save and not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Iterate over all files in the input directory
    for filename in os.listdir(input_directory):
        # Process only .txt files
        if filename.endswith(".txt"):
            # Read the content of the file
            with open(os.path.join(input_directory, filename), 'r', encoding='utf-8') as file:
                print(filename)
                text = file.read()

                # Apply normalization functions
                text = normalize_page_content(text)
                text = remove_headers(text)
                text = remove_timestamps(text)
                text = normalize_characters(text)  # Ensure you have this function defined
                text = normalize_quotes(text)
                text = normalize_line_breaks(text)

                # If save is True, write the normalized text to a new file in the output directory
                if save:
                    output_filename = os.path.join(output_directory, filename)
                    with open(output_filename, 'w', encoding='utf-8') as output_file:
                        output_file.write(text)

                # Otherwise, print the name of the processed file and its normalized content
                else:
                    print(f"Processed {filename}:\n{text}\n")