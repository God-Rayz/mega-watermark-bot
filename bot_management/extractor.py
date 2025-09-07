"""
Module: extractor.py
This module provides functions to extract folder sizes from MEGA links.
"""

import json
import os
import time
import re
import requests
from bs4 import BeautifulSoup
from bot_management import LOGS

def parse_folder_size(folder_size_text, folder_unit):
    """
    Convert a folder size given as text and unit to GB.
    
    Args:
        folder_size_text (str): The numerical size as a string.
        folder_unit (str): The unit, e.g., 'MB', 'GB', etc.
        
    Returns:
        float: Folder size in GB if conversion is successful,
               or False if an error occurs.
    """
    try:
        size_value = float(folder_size_text.replace(",", "."))
    except ValueError:
        LOGS.error("Error converting folder size text to float.")
        return False

    unit = folder_unit.upper()
    if unit.startswith("KB"):
        return size_value / (1024 * 1024)
    if unit.startswith("MB"):
        return size_value / 1024
    if unit.startswith("GB"):
        return size_value
    if unit.startswith("TB"):
        return size_value * 1024
    if unit.startswith("BYTE"):
        return size_value / (1024 * 1024 * 1024)
    LOGS.error("Unknown folder size unit: %s", folder_unit)
    return False

def extract_folder_size(mega_link):
    """
    Extract folder size from a MEGA folder link using BeautifulSoup, with retry logic.
    
    Args:
        mega_link (str): The MEGA folder URL.
    
    Returns:
        float: The folder size in GB if successfully extracted,
               or False if an error occurred after all retries.
    """
    max_retries = 4
    delay = 3  # seconds between retries

    for attempt in range(1, max_retries + 1):
        LOGS.info("Attempt %s: Extracting folder size from link: %s", attempt, mega_link)
        try:
            response = requests.get(mega_link, timeout=10)
            if response.status_code != 200:
                LOGS.error("Failed to fetch the URL: %s (status code: %s)", mega_link, response.status_code)
            else:
                soup = BeautifulSoup(response.text, "html.parser")
                meta_title = soup.find("meta", {"property": "og:title"})
                if meta_title:
                    folder_info = meta_title.get("content", "")
                    LOGS.info("Extracted folder info: %s", folder_info)
                    
                    # Use regex to find size and unit more robustly
                    match = re.search(r"(\d[\d,.]*)\s*([KMGT]?B)", folder_info, re.IGNORECASE)
                    
                    if match:
                        folder_size_text = match.group(1)
                        folder_unit = match.group(2)
                        folder_size = parse_folder_size(folder_size_text, folder_unit)
                        if folder_size is not False:
                            LOGS.info("MEGA folder size extracted successfully: %s GB", folder_size)
                            return folder_size
                        else:
                            LOGS.error("Failed to parse folder size from text: %s %s", folder_size_text, folder_unit)
                    elif "File folder on MEGA" in folder_info or "folder on MEGA" in folder_info:
                        LOGS.info("Folder info suggests an empty or no-size folder. Returning 0.0 GB.")
                        return 0.0
                    else:
                        LOGS.error("Could not find folder size in info: '%s'", folder_info)
                else:
                    LOGS.error("Folder size not found in the meta tags.")
        except Exception as e:
            LOGS.error("Error retrieving MEGA folder size on attempt %s: %s", attempt, e, exc_info=True)
        
        if attempt < max_retries:
            LOGS.info("Retrying in %s seconds...", delay)
            time.sleep(delay)

    LOGS.error("All attempts to extract folder size failed.")
    return False

def extract_folder_sizes(mega_links, process_folder):
    """
    Loops through a list of URLs, extracts the folder size for each valid MEGA link,
    and saves the results to a JSON file in the given process folder.
    Any leading '$' is removed from the URL before extraction.
    URLs that are not valid MEGA links are stored separately.
    
    Args:
        mega_links (list[str]): List of URLs (which may include a leading '$').
        process_folder (str): Path to the process folder where the JSON will be saved.
    
    Returns:
        tuple: (folder_sizes, non_mega_links)
            folder_sizes: dict mapping each valid MEGA link (with its original flag) to its folder size.
            non_mega_links: dict mapping each URL that is not a valid MEGA link to None.
    """
    folder_sizes = {}
    non_mega_links = {}
    for link in mega_links:
        LOGS.info("Processing link: %s", link)
        # Remove any leading '$' for extraction purposes.
        cleaned_link = link.lstrip("$")
        if cleaned_link.startswith("https://mega.nz/folder/"):
            size = extract_folder_size(cleaned_link)
            folder_sizes[link] = size  # store using the original link (flag preserved)
        else:
            non_mega_links[link] = None

    combined = {
        "mega_folder_sizes": folder_sizes,
        "non_mega_links": non_mega_links
    }
    output_file = os.path.join(process_folder, "folder_sizes.json")
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(combined, json_file, indent=4)

    return folder_sizes, non_mega_links
