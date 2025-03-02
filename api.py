from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
from werkzeug.utils import secure_filename
import uuid
from board_scraper import PinterestBoardScraper
from image_sim_search import find_similar_images
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app) # enable cors for all 

# Configuration
UPLOAD_FOLDER = "uploaded_images"
SCRAPED_FOLDER = "pictures"
MAX_IMAGES = 5
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCRAPED_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_pinterest_info(board_url):
    """Extract username and board name from Pinterest URL."""
    pattern = r"pinterest\.com/([^/]+)/([^/]+)"
    match = re.search(pattern, board_url)

    if match:
        return match.group(1), match.group(2)
    return None, None


def save_base64_image(base64_string, folder):
    """Save a base64 image to a file and return the path."""
    try:
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(folder, filename)

        # Remove data URL prefix if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]

        # Decode and save
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(base64_string))

        return filepath
    except Exception as e:
        logger.error(f"Error saving base64 image: {e}")
        return None


@app.route("/api/fashion-finder", methods=["POST"])
def fashion_finder():
    """Main endpoint that combines Pinterest scraping and image similarity search."""
    try:
        data = request.json

        # Check required fields
        if not data:
            return jsonify({"error": "No data provided"}), 400

        pinterest_url = data.get("pinterest_url")
        images_base64 = data.get("images", [])

        # Validate Pinterest URL
        if not pinterest_url:
            return jsonify({"error": "Pinterest board URL is required"}), 400

        # Validate number of images
        if len(images_base64) > MAX_IMAGES:
            return jsonify({"error": f"Maximum of {MAX_IMAGES} images allowed"}), 400

        # Extract Pinterest username and board name
        username, board_name = extract_pinterest_info(pinterest_url)
        if not username or not board_name:
            return jsonify({"error": "Invalid Pinterest board URL format"}), 400

        # Initialize the scraper and scrape the board
        scraper = PinterestBoardScraper()

        # Get board info
        board_info = scraper.get_board_info(username, board_name)
        if board_info["title"] == "Error":
            return jsonify({"error": "Failed to access Pinterest board"}), 404

        # Scrape pins
        pins = scraper.scrape_pins(username, board_name, quality="736x")
        if not pins:
            return jsonify({"error": "No pins found on the board"}), 404
        
        uploaded_urls = scraper.download_images(
            pins, username=username, board_name=board_name
        )


        # Save uploaded base64 images
        upload_paths = []
        for img_base64 in images_base64:
            path = save_base64_image(img_base64, UPLOAD_FOLDER)
            if path:
                upload_paths.append(path)

        # if no images were uploaded, just return the scraped images
        if not upload_paths:
            return jsonify(
                {
                    "board_info": board_info,
                    "scraped_images": [{"path": path} for path in uploaded_urls],
                    "similar_images": [],
                }
            )

        # Find similar images
        # similarity_payload = {"images": images_base64, "library_directory": target_dir}
        target_dir = os.path.join(SCRAPED_FOLDER, username, board_name)
        similarity_payload = {
            "images": images_base64, 
            "library_directory": target_dir,
            "username": username,
            "board_name": board_name
        }

        similarity_results = find_similar_images(similarity_payload)
        # returns {"results": results, "best_overall_matches": best_overall_matches}

        # Return combined results
        return jsonify(
            {
                "board_info": board_info,
                "scraped_images_count": len(uploaded_urls),
                "uploaded_images_count": len(upload_paths),
                "similarity_results": similarity_results.get("results", []),
                "best_overall_matches": similarity_results.get("best_overall_matches", []),
                "uploaded_matches": similarity_results.get("uploaded_matches", [])
            }
        )

    except Exception as e:
        logger.error(f"Error in fashion finder: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/scrape-board", methods=["POST"])
def scrape_board():
    """Endpoint to only scrape a Pinterest board."""
    try:
        data = request.json

        if not data or not data.get("pinterest_url"):
            return jsonify({"error": "Pinterest board URL is required"}), 400

        pinterest_url = data.get("pinterest_url")
        username, board_name = extract_pinterest_info(pinterest_url)

        if not username or not board_name:
            return jsonify({"error": "Invalid Pinterest board URL format"}), 400

        # Initialize and use the scraper
        scraper = PinterestBoardScraper()
        board_info = scraper.get_board_info(username, board_name)
        pins = scraper.scrape_pins(username, board_name, quality="736x")

        # download images if requested to supabase
        if data.get("download_images", False):
            uploaded_urls = scraper.download_images(
                pins,
                username=username,
                board_name=board_name,
            )
            return jsonify(
                {
                    "board_info": board_info,
                    "pins_count": len(pins),
                    "uploaded_images": len(uploaded_urls),
                    "uploaded_urls": uploaded_urls
                }
            )

        return jsonify({"board_info": board_info, "pins": pins})

    except Exception as e:
        logger.error(f"Error in scrape board: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/find-similar", methods=["POST"])
def find_similar():
    """Endpoint to only find similar images."""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        images_base64 = data.get("images", [])
        pinterest_url = data.get("pinterest_url")

        if not images_base64:
            return jsonify({"error": "No images provided"}), 400

        if len(images_base64) > MAX_IMAGES:
            return jsonify({"error": f"Maximum of {MAX_IMAGES} images allowed"}), 400

        # If a Pinterest URL is provided, use the scraped images as the library
        if pinterest_url:
            username, board_name = extract_pinterest_info(pinterest_url)
            if not username or not board_name:
                return jsonify({"error": "Invalid Pinterest board URL format"}), 400

            similarity_payload = {
                "images": images_base64,
                "username": username,
                "board_name": board_name,
                "use_supabase": True  
            }
        else:
            use_supabase = data.get("use_supabase", False)
            username = data.get("username")
            board_name = data.get("board_name")
            
            if use_supabase and (not username or not board_name):
                return jsonify({"error": "Username and board name required for Supabase storage"}), 400
            
            if use_supabase:
                similarity_payload = {
                    "images": images_base64,
                    "username": username,
                    "board_name": board_name,
                    "use_supabase": True
                }
            else:
                # Fallback to local directory
                library_dir = data.get("library_directory", SCRAPED_FOLDER)
                similarity_payload = {
                    "images": images_base64,
                    "library_directory": library_dir,
                    "use_supabase": False
                }

        similarity_results = find_similar_images(similarity_payload)
        return jsonify(similarity_results)

    except Exception as e:
        logger.error(f"Error in find similar: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
