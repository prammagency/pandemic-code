import os
import re
import json
import glob
from bs4 import BeautifulSoup
import requests
import time
import random
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_extraction_supplemental.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
HTML_DIR = "D:/RS_AI/ALL DOCS/Dreambot Api Docs- Classes_Enums/html_documents"  # Directory with HTML files
OUTPUT_DIR = "D:/RS_AI/ALL DOCS/Dreambot Api Docs- Classes_Enums/extracted_content"
PROCESSED_URLS_FILE = "D:/RS_AI/ALL DOCS/Dreambot Api Docs- Classes_Enums/processed_urls.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://dreambot.org/"
}

def load_processed_urls():
    """Load list of URLs already processed"""
    if os.path.exists(PROCESSED_URLS_FILE):
        with open(PROCESSED_URLS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_url(url):
    """Add URL to the processed list"""
    processed_urls = load_processed_urls()
    processed_urls.add(url)
    with open(PROCESSED_URLS_FILE, "w") as f:
        json.dump(list(processed_urls), f)

def extract_api_links(html_file):
    """Extract DreamBot API documentation links from an HTML file"""
    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    base_url = "https://dreambot.org/javadocs/"
    api_links = set()
    
    # Extract links from various sources in the HTML document
    
    # Method 1: Direct links to JavaDoc pages
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("org/dreambot/api/") or "/org/dreambot/api/" in href:
            full_url = urljoin(base_url, href)
            if full_url.endswith(".html"):
                api_links.add(full_url)
    
    # Method 2: Look for references in code examples
    for code in soup.find_all(["code", "pre"]):
        text = code.get_text()
        # Look for import statements or fully qualified class names
        matches = re.findall(r'org\.dreambot\.api\.[a-zA-Z0-9_.]+', text)
        for match in matches:
            # Convert package names to URLs
            path = match.replace('.', '/') + ".html"
            full_url = urljoin(base_url, path)
            api_links.add(full_url)
    
    return api_links

def extract_all_links():
    """Process all HTML files to extract new API links"""
    processed_urls = load_processed_urls()
    new_links = set()
    
    # Get list of all HTML files
    html_files = glob.glob(os.path.join(HTML_DIR, "*.html"))
    logger.info(f"Found {len(html_files)} HTML files to process")
    
    # Extract links from all HTML files
    for html_file in html_files:
        logger.info(f"Processing HTML file: {os.path.basename(html_file)}")
        try:
            links = extract_api_links(html_file)
            for link in links:
                if link not in processed_urls:
                    new_links.add(link)
        except Exception as e:
            logger.error(f"Error processing {html_file}: {str(e)}")
    
    logger.info(f"Found {len(new_links)} new links to process")
    return new_links