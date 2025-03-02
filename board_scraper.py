import requests
from bs4 import BeautifulSoup
import re
import os
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PinterestBoardScraper:
    """A class for scraping Pinterest boards for computer vision applications."""

    def __init__(self, base_url: str = "https://pinterest.com/"):
        """Initialize the scraper with the base Pinterest URL."""
        self.base_url = base_url

    def get_board_info(self, username: str, board_name: str) -> Dict:
        """
        Get basic information about a Pinterest board.

        Args:
            username: Pinterest username
            board_name: Name of the board to scrape

        Returns:
            Dict containing board title and total pin count
        """
        try:
            response = requests.get(f"{self.base_url}{username}/{board_name}")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.find("h1").text if soup.find("h1") else "Unknown Board"
            count_element = soup.find("header")
            if count_element:
                count_element = count_element.find(
                    "div", {"data-test-id": "board-count-info"}
                )
                count = (
                    int(re.sub(r"\D", "", count_element.text)) if count_element else 0
                )
            else:
                count = 0

            logger.info(f"Found board: {title} with {count} pins")

            return {"title": title, "total_pins": count}

        except requests.RequestException as e:
            logger.error(f"Error fetching board info: {e}")
            return {"title": "Error", "total_pins": 0}

    def scrape_pins(
        self, username: str, board_name: str, quality: str = "736x"
    ) -> List[Dict]:
        """
        Scrape images from a Pinterest board at the specified quality.

        Args:
            username: Pinterest username
            board_name: Name of the board to scrape
            quality: Image quality/resolution ('236x', '564x', '736x', '1200x', 'original')

        Returns:
            List of dictionaries containing image source URLs and alt text
        """
        try:
            response = requests.get(f"{self.base_url}{username}/{board_name}")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            results = []
            for img in soup.find_all("img"):
                src = img.get("src")
                alt = img.get("alt")

                if src:
                    # Replace resolution in URL with desired quality
                    if quality == "original":
                        # Try to get original size by removing size pattern
                        src = re.sub(r"/\d+x/", "/", src)
                    else:
                        src = re.sub(r"/\d+x/", f"/{quality}/", src)

                    results.append({"src": src, "alt": alt})

            logger.info(
                f"Successfully scraped {len(results)} images at {quality} quality"
            )
            return results

        except requests.RequestException as e:
            logger.error(f"Error scraping pins: {e}")
            return []

    def download_images(
        self,
        image_list: List[Dict],
        output_dir: str = "scraped_images",
        username: str = None,
        board_name: str = None,
    ) -> List[str]:
        """
        Download images from scraped URLs to the specified directory.

        Args:
            image_list: List of dictionaries containing image sources
            output_dir: Directory to save downloaded images
            username: Optional username to create subdirectory
            board_name: Optional board name to create subdirectory

        Returns:
            List of paths to downloaded images
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create nested directory structure if username and board_name are provided
        if username and board_name:
            nested_dir = os.path.join(output_dir, username, board_name)
            os.makedirs(nested_dir, exist_ok=True)
            # Use the nested directory for downloads
            target_dir = nested_dir
        else:
            target_dir = output_dir

        downloaded_paths = []

        for i, image in enumerate(image_list):
            src = image.get("src")
            if not src:
                continue

            try:
                # Generate filename from URL or index
                filename = f"pin_{i}.jpg"
                filepath = os.path.join(target_dir, filename)

                # Download the image
                img_response = requests.get(src, stream=True)
                img_response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)

                downloaded_paths.append(filepath)
                logger.info(f"Downloaded image {i + 1}/{len(image_list)}: {filepath}")

            except (requests.RequestException, IOError) as e:
                logger.error(f"Error downloading image {i + 1}: {e}")

        return downloaded_paths


if __name__ == "__main__":
    scraper = PinterestBoardScraper()

username = "thammili"
board_name = "fashion"

board_info = scraper.get_board_info(username, board_name)
print(f"Board: {board_info['title']} ({board_info['total_pins']} pins)")

images = scraper.scrape_pins(username, board_name, quality="736x")
print(f"Found {len(images)} images")

base_dir = "pictures"
# image_paths_base = scraper.download_images(images, output_dir=base_dir)
# print(f"Downloaded {len(image_paths_base)} images to {base_dir}")

# Download to nested directory structure
image_paths_nested = scraper.download_images(
    images, output_dir=base_dir, username=username, board_name=board_name
)
print(
    f"Downloaded {len(image_paths_nested)} images to {base_dir}/{username}/{board_name}"
)
