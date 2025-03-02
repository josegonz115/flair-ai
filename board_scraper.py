import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import logging
from supabase_config import supabase, BUCKET_NAME



logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PinterestBoardScraper:
    """A class for scraping Pinterest boards for computer vision applications."""

    def __init__(self, base_url: str = "https://pinterest.com/"):
        """Initialize the scraper with the base Pinterest URL."""
        self.base_url = base_url


    def download_images(
        self,
        image_list: List[Dict],
        # output_dir: str = "scraped_images",
        username: str = None,
        board_name: str = None,
    ) -> List[str]:
        """
        Download images from scraped URLs to Supabase Storage.

        Args:
            image_list: List of dictionaries containing image sources
            output_dir: Directory to save downloaded images (used for naming)
            username: Optional username to create subdirectory
            board_name: Optional board name to create subdirectory

        Returns:
            List of public URLs to the uploaded images in Supabase Storage
        """

        uploaded_urls = []

        for i, image in enumerate(image_list):
            src = image.get("src")
            if not src:
                continue

            try:
                filename = f"pin_{i}.jpg"

                img_response = requests.get(src, stream=True)
                img_response.raise_for_status()

                file_path = f"{username}/{board_name}/{filename}" if username and board_name else filename
                result = supabase.storage.from_(BUCKET_NAME).upload(
                    file=img_response.raw.read(),
                    path=file_path,
                    file_options={"content-type": "image/jpeg", "upsert": 'true'}, 
                )

                if not result.path: # no result.error?
                    logger.error(f"Supabase upload error: {result}")
                    continue

                public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
                uploaded_urls.append(public_url)
                logger.info(f"Uploaded image {i + 1}/{len(image_list)} to Supabase: {public_url}")

            except (requests.RequestException, IOError) as e:
                logger.error(f"Error downloading/uploading image {i + 1}: {e}")

        return uploaded_urls

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

# if __name__ == "__main__":
#     scraper = PinterestBoardScraper()

# username = "thammili"
# board_name = "fashion"

# board_info = scraper.get_board_info(username, board_name)
# print(f"Board: {board_info['title']} ({board_info['total_pins']} pins)")

# images = scraper.scrape_pins(username, board_name, quality="736x")
# print(f"Found {len(images)} images")

# base_dir = "pictures"
# # image_paths_base = scraper.download_images(images, output_dir=base_dir)
# # print(f"Downloaded {len(image_paths_base)} images to {base_dir}")

# # Download to nested directory structure
# image_paths_nested = scraper.download_images(
#     images, output_dir=base_dir, username=username, board_name=board_name
# )
# print(
#     f"Downloaded {len(image_paths_nested)} images to {base_dir}/{username}/{board_name}"
# )
