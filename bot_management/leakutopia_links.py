import os
import json
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from bot_management import LOGS

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

def extract_mega_from_leakutopia_headless_old(url):
    """
    Extracts the first MEGA folder URL from a leakutopia.click page using headless Selenium,
    traversing the container (div.whitespace-pre-wrap) in a single DOM pass.

    Key points:
      1. Skips links starting with "https://leakutopia.com" or "https://dood".
      2. Replaces "https://gofile.io/d/uSaNcR" with "https://pixeldrain.com/u/8QXHYGwV".
      3. The first encountered "https://mega.nz/folder/" link is extracted_mega (excluded from extra data).
      4. "https://mega.nz/file/" links go into extra data.
      5. Text nodes are also included in extra data, unless they match an anchor's href (which would cause duplication).
      6. Start/end markers:
         - Start marker: "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒱👇"
         - End marker:   "🌟LEAK UTOPIA HUB🌟"
         If the start marker is in the container text, capturing is False until the marker is found.
         Once found, capturing is True until the end marker is encountered.
         If the markers aren't present, everything is captured.
      7. Unwanted URLs (Telegram links, etc.) are filtered at the end.
    
    Args:
        url (str): The leakutopia.click URL to process.

    Returns:
        tuple: (extracted_mega_url, extra_data)
          extracted_mega_url (str): The first "https://mega.nz/folder/" link encountered, or None.
          extra_data (dict): {"all_urls": [...]} containing text lines and links in DOM order, minus duplicates.
    """
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    extracted_mega = None
    extra_items = []

    try:
        # Wait for the container.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.whitespace-pre-wrap"))
        )
        container = driver.find_element(By.CSS_SELECTOR, "div.whitespace-pre-wrap")
        container_html = container.get_attribute("innerHTML")

        # Check markers in the container text.
        full_text = container.text
        start_marker = "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒱👇"
        end_marker = "🌟LEAK UTOPIA HUB🌟"
        capturing = True
        if start_marker in full_text:
            capturing = False  # Wait until we see the start marker.

        # Parse container HTML with BeautifulSoup
        soup = BeautifulSoup(container_html, "html.parser")

        # Single-pass DOM traversal
        for node in soup.recursiveChildGenerator():
            if isinstance(node, NavigableString):
                # It's a text node
                text_value = node.strip()
                if not text_value:
                    # Skip empty text lines
                    continue

                # Check if this text is inside an anchor whose href matches the text => skip to avoid duplication
                parent = node.parent
                if parent and parent.name == "a":
                    href = parent.get("href", "").strip() if parent.has_attr("href") else ""
                    if text_value == href:
                        continue

                # Check for start/end markers
                if start_marker in text_value:
                    capturing = True
                    text_value = text_value.replace(start_marker, "").strip()
                if end_marker in text_value and capturing:
                    # Only capture what appears before the end marker
                    split_text = text_value.split(end_marker, 1)[0].strip()
                    if split_text:
                        # If the previous item is a link, insert a blank line first
                        if extra_items and extra_items[-1].startswith("http"):
                            extra_items.append("")
                        extra_items.append(split_text)
                    capturing = False
                    continue

                if capturing and text_value:
                    # If the previous item is a link, insert a blank line before the text
                    if extra_items and extra_items[-1].startswith("http"):
                        extra_items.append("")
                    extra_items.append(text_value)

            elif hasattr(node, "name") and node.name == "a":
                # It's an anchor tag
                href = node.get("href", "").strip()
                if not href:
                    continue

                # If we're not capturing yet, skip
                if not capturing:
                    # But still check if the start marker is in the anchor text, in theory.
                    text_in_anchor = node.get_text(strip=True)
                    if start_marker in text_in_anchor:
                        capturing = True
                    # If we see the end marker in anchor text, capturing = False (edge case)
                    continue

                # Replace gofile
                if href == "https://gofile.io/d/uSaNcR":
                    href = "https://pixeldrain.com/u/8QXHYGwV"

                # Skip links starting with unwanted prefixes
                # if href.startswith("https://leakutopia.com") or href.startswith("https://dood"):
                #     continue

                # If it's a MEGA folder link and we haven't found one yet, store it, skip adding to extras
                if "https://mega.nz/folder/" in href:
                    if extracted_mega is None:
                        extracted_mega = href
                    continue

                # If it's a MEGA file link or any other link, add to extras
                extra_items.append(href)

            else:
                # Some other tag; optionally capture text if needed
                if not capturing:
                    continue
                text_in_tag = node.get_text(strip=True) if hasattr(node, "get_text") else ""
                if text_in_tag:
                    # Check if end marker is in this text
                    if end_marker in text_in_tag:
                        text_in_tag = text_in_tag.split(end_marker, 1)[0].strip()
                        extra_items.append(text_in_tag)
                        capturing = False
                    else:
                        extra_items.append(text_in_tag)

    except Exception as e:
        LOGS.error("Error extracting content from %s: %s", url, e, exc_info=True)
        extracted_mega = None
    finally:
        driver.quit()

    # Filter out unwanted URLs
    remove_list = [
        "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒲👇",
        "https://t.me/LeakUtopiaHub",
        "https://t.me/FreeUltimateOF",
        "https://t.me/MegaOFHub",
        "https://t.me/UnlimitedOnlyfans",
        "https://leakutopia.com/",
        "https://t.me/LeakUtopiaUpdates",
        "Join for More Leaks -->"
    ]
    filtered_items = [item for item in extra_items if item not in remove_list]

    extra_data = {"all_urls": filtered_items}
    return extracted_mega, extra_data

def extract_mega_from_leakutopia_headless(url):
    """
    Extracts the first MEGA folder URL from a leakutopia.click page using headless Selenium and BeautifulSoup.
    Finds all <a> tags in div.prose and returns the first mega.nz/folder/ link and all other links as extras, preserving blank lines between groups.
    Also extracts text content from paragraphs to preserve descriptive text like "👇🏻NEW:".
    """
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    extracted_mega = None
    extra_items = []

    try:
        # Wait for the .prose container to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.prose"))
        )
        from bs4 import BeautifulSoup
        from bs4.element import Tag
        soup = BeautifulSoup(driver.page_source, "html.parser")
        prose_div = soup.find("div", class_="prose")
        if prose_div and isinstance(prose_div, Tag):
            paragraphs = prose_div.find_all("p")
            for idx, p in enumerate(paragraphs):
                # Extract text content from the paragraph (excluding links)
                paragraph_text = ""
                for content in p.contents:
                    if isinstance(content, str):
                        text = content.strip()
                        if text and not text.startswith("http"):
                            paragraph_text += text + " "
                    elif hasattr(content, 'name') and content.name == 'a':
                        # Skip links, we'll extract them separately
                        continue
                
                paragraph_text = paragraph_text.strip()
                if paragraph_text:
                    # This is descriptive text (like "👇🏻NEW:"), add it
                    extra_items.append(paragraph_text)
                
                # Extract links from the paragraph
                for a in p.find_all("a", href=True):
                    href = a["href"]
                    if "mega.nz/folder/" in href and not extracted_mega:
                        extracted_mega = href
                    else:
                        extra_items.append(href)
                
                # Add a blank line after each <p> except the last one
                if idx < len(paragraphs) - 1:
                    extra_items.append("")
        else:
            # fallback: search all links in the page
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "mega.nz/folder/" in href and not extracted_mega:
                    extracted_mega = href
                else:
                    extra_items.append(href)
    except Exception as e:
        LOGS.error("Error extracting content from %s: %s", url, e, exc_info=True)
        extracted_mega = None
        extra_items = []
    finally:
        driver.quit()

    # Filter out unwanted URLs and text
    remove_list = [
        "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒲👇",
        "https://t.me/LeakUtopiaHub",
        "https://t.me/FreeUltimateOF",
        "https://t.me/MegaOFHub",
        "https://t.me/UnlimitedOnlyfans",
        "https://leakutopia.com/",
        "https://t.me/LeakUtopiaUpdates",
        "Join for More Leaks -->"
    ]
    filtered_items = [item for item in extra_items if item not in remove_list]

    extra_data = {"all_urls": filtered_items}
    return extracted_mega, extra_data

def extract_mega_from_leakutopia_headless_hybrid(url):
    """
    Extracts the first MEGA folder URL from a leakutopia.click page using headless Selenium,
    trying both div.whitespace-pre-wrap and div.prose selectors to handle website structure changes.
    """
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    extracted_mega = None
    extra_items = []

    try:
        # Try both possible selectors
        container = None
        container_html = None
        
        # First try div.whitespace-pre-wrap
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.whitespace-pre-wrap"))
            )
            container = driver.find_element(By.CSS_SELECTOR, "div.whitespace-pre-wrap")
            container_html = container.get_attribute("innerHTML")
        except:
            # If that fails, try div.prose
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.prose"))
                )
                container = driver.find_element(By.CSS_SELECTOR, "div.prose")
                container_html = container.get_attribute("innerHTML")
            except:
                # If both fail, try to find any div with content
                try:
                    container = driver.find_element(By.CSS_SELECTOR, "div")
                    container_html = container.get_attribute("innerHTML")
                except:
                    LOGS.error("Could not find content container on page: %s", url)
                    return None, {"all_urls": []}

        if not container_html:
            LOGS.error("No content found on page: %s", url)
            return None, {"all_urls": []}

        # Check markers in the container text.
        full_text = container.text
        start_marker = "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒱👇"
        end_marker = "🌟LEAK UTOPIA HUB🌟"
        capturing = True
        if start_marker in full_text:
            capturing = False  # Wait until we see the start marker.

        # Parse container HTML with BeautifulSoup
        soup = BeautifulSoup(container_html, "html.parser")

        # Single-pass DOM traversal
        for node in soup.recursiveChildGenerator():
            if isinstance(node, NavigableString):
                # It's a text node
                text_value = node.strip()
                if not text_value:
                    # Skip empty text lines
                    continue

                # Check if this text is inside an anchor whose href matches the text => skip to avoid duplication
                parent = node.parent
                if parent and parent.name == "a":
                    href = parent.get("href", "").strip() if parent.has_attr("href") else ""
                    if text_value == href:
                        continue

                # Check for start/end markers
                if start_marker in text_value:
                    capturing = True
                    text_value = text_value.replace(start_marker, "").strip()
                if end_marker in text_value and capturing:
                    # Only capture what appears before the end marker
                    split_text = text_value.split(end_marker, 1)[0].strip()
                    if split_text:
                        # If the previous item is a link, insert a blank line first
                        if extra_items and extra_items[-1].startswith("http"):
                            extra_items.append("")
                        extra_items.append(split_text)
                    capturing = False
                    continue

                if capturing and text_value:
                    # If the previous item is a link, insert a blank line before the text
                    if extra_items and extra_items[-1].startswith("http"):
                        extra_items.append("")
                    extra_items.append(text_value)

            elif hasattr(node, "name") and node.name == "a":
                # It's an anchor tag
                href = node.get("href", "").strip()
                if not href:
                    continue

                # If we're not capturing yet, skip
                if not capturing:
                    # But still check if the start marker is in the anchor text, in theory.
                    text_in_anchor = node.get_text(strip=True)
                    if start_marker in text_in_anchor:
                        capturing = True
                    # If we see the end marker in anchor text, capturing = False (edge case)
                    continue

                # Replace gofile
                if href == "https://gofile.io/d/uSaNcR":
                    href = "https://pixeldrain.com/u/8QXHYGwV"

                # If it's a MEGA folder link and we haven't found one yet, store it, skip adding to extras
                if "https://mega.nz/folder/" in href:
                    if extracted_mega is None:
                        extracted_mega = href
                    continue

                # If it's a MEGA file link or any other link, add to extras
                extra_items.append(href)

            else:
                # Some other tag; optionally capture text if needed
                if not capturing:
                    continue
                text_in_tag = node.get_text(strip=True) if hasattr(node, "get_text") else ""
                if text_in_tag:
                    # Check if end marker is in this text
                    if end_marker in text_in_tag:
                        text_in_tag = text_in_tag.split(end_marker, 1)[0].strip()
                        extra_items.append(text_in_tag)
                        capturing = False
                    else:
                        extra_items.append(text_in_tag)

    except Exception as e:
        LOGS.error("Error extracting content from %s: %s", url, e, exc_info=True)
        extracted_mega = None
    finally:
        driver.quit()

    # Filter out unwanted URLs
    remove_list = [
        "👇 𝑀𝐸𝒢𝒜 𝐿𝐼𝒩𝒦 𝐼𝒮 𝐵𝐸𝐿𝒪𝒲👇",
        "https://t.me/LeakUtopiaHub",
        "https://t.me/FreeUltimateOF",
        "https://t.me/MegaOFHub",
        "https://t.me/UnlimitedOnlyfans",
        "https://leakutopia.com/",
        "https://t.me/LeakUtopiaUpdates"
    ]
    filtered_items = [item for item in extra_items if item not in remove_list]

    extra_data = {"all_urls": filtered_items}
    return extracted_mega, extra_data

def process_leakutopia_links(mega_links, process_folder):
    """
    Processes a list of mega links to handle leakutopia.click URLs.

    For any link starting with "https://leakutopia.click/", it uses the helper
    extract_mega_from_leakutopia_headless to extract the mega URL. If extraction fails,
    it leaves the original leakutopia URL in the processed list (with the "$" flag re-applied if present)
    and stores the extra data. The mapping from the extracted mega URL (or original link if extraction fails)
    to the original leakutopia URL and extra data is saved in a JSON file in the process folder.

    Args:
        mega_links (list[str]): The original list of mega links.
        process_folder (str): The folder where the mapping file will be saved.

    Returns:
        tuple: (processed_mega_links, leakutopia_mapping)
            processed_mega_links: The updated list of mega links with leakutopia URLs replaced.
            leakutopia_mapping: A dict mapping the extracted mega URL (or original leakutopia URL if extraction fails)
                                to their corresponding original leakutopia data.
    """
    leakutopia_mapping = {}
    processed = []

    for link in mega_links:
        flag = False
        if link.startswith("$"):
            flag = True
            link = link.lstrip("$")
        if link.startswith("https://leakutopia.click/"):
            extracted, extra = extract_mega_from_leakutopia_headless(link)
            if extracted:
                leakutopia_mapping[extracted] = {"original": link, "extra": extra}
                processed.append("$" + extracted if flag else extracted)
            else:
                leakutopia_mapping[link] = {"original": link, "extra": extra}
                processed.append("$" + link if flag else link)
        else:
            processed.append("$" + link if flag else link)

    mapping_file = os.path.join(process_folder, "leakutopia_mapping.json")
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(leakutopia_mapping, f, indent=4)

    return processed, leakutopia_mapping

def newPaste(content):

    url = "https://leakutopia.click/api/graphql"

    headers = {
        "Origin": "https://leakutopia.click",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 API",
    }

    payload = {
        "operationName": "Mutation",
        "query": "mutation Mutation($texts: [String!], $editCode: String) {\n createBin(texts: $texts, editCode: $editCode) {\n createdOn\n i_id\n id\n text\n __typename\n }\n}",
        "variables": {"texts": [content], "editCode": "hundredkpermonth"}
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json().get("data", {}).get("createBin", [{}])[0]
        i_id = data.get("i_id")
        return "https://leakutopia.click/b/" + i_id
    else:
        print("Error:", response.text)
