import os
import base64
import io
import json
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the pre-trained model (without the classification head)
model = ResNet50(weights="imagenet", include_top=False, pooling="avg")


def extract_features(img):
    """Extract feature vector from image using ResNet50"""
    img = img.resize((224, 224))
    img_array = img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    features = model.predict(img_array)
    return features[0]


def find_similar_images(request_data):
    # Parse the input JSON
    images_base64 = request_data.get("images", [])
    library_dir = request_data.get("library_directory", "")

    if not images_base64 or not library_dir:
        return {"error": "Missing required inputs"}

    # Decode and process input images
    query_features = []
    for img_base64 in images_base64:
        try:
            img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            features = extract_features(img)
            query_features.append(features)
        except Exception as e:
            logger.error(f"Error processing input image: {e}")
            return {"error": f"Failed to process input image: {str(e)}"}

    # Process library images
    library_features = []
    library_paths = []
    valid_extensions = [".png", ".jpg", ".jpeg", ".gif"]

    for filename in os.listdir(library_dir):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in valid_extensions:
            file_path = os.path.join(library_dir, filename)
            try:
                img = Image.open(file_path).convert("RGB")
                features = extract_features(img)
                library_features.append(features)
                library_paths.append(file_path)
            except Exception as e:
                logger.error(f"Error processing library image {filename}: {e}")
                continue

    if not library_features:
        return {"error": "No valid images found in library"}

    results = []
    library_features_array = np.array(library_features)

    # track combined similarity scores across all query images
    combined_similarity_scores = np.zeros(len(library_features))

    for i, query_feature in enumerate(query_features):
        similarities = cosine_similarity([query_feature], library_features_array)[0]

        combined_similarity_scores += similarities

        # get individual matches for this query 
        top_indices = np.argsort(similarities)[::-1][:5]
        matches = []
        for idx in top_indices:
            matches.append(
                {
                    "path": library_paths[idx],
                    "similarity_score": float(similarities[idx]),
                }
            )
        results.append({"query_image_index": i, "matches": matches})

    # highest average similarity
    avg_similarity_scores = combined_similarity_scores / len(query_features)
    top_3_indices = np.argsort(avg_similarity_scores)[::-1][:3] 
    best_overall_matches = []

    for best_idx in top_3_indices:
        best_match = {
            "path": library_paths[best_idx],
            "average_similarity_score": float(avg_similarity_scores[best_idx]),
            "individual_scores": {},
        }
        
        # add individual scores for this match
        for i, query_feature in enumerate(query_features):
            similarity = float(
                cosine_similarity([query_feature], [library_features[best_idx]])[0][0]
            )
            best_match["individual_scores"][f"query_{i}"] = similarity
            
        best_overall_matches.append(best_match)
    
    return {"results": results, "best_overall_matches": best_overall_matches}



# if __name__ == "__main__":
#     try:
#         with open("sample_pictures/black_jacket.txt", "r") as f:
#             black_jacket_base64 = f.read().strip()
#         with open("sample_pictures/brown_bag.txt", "r") as f:
#             brown_bag_base64 = f.read().strip()

#         # Create the payload
#         example_payload = {
#             "images": [black_jacket_base64, brown_bag_base64],
#             "library_directory": "./pictures/thammili/fashion",
#         }

#         # Run the function with the payload
#         results = find_similar_images(example_payload)

#         # Display results
#         if "error" in results:
#             print(f"Error: {results['error']}")
#         else:
#             for i, result in enumerate(results["results"]):
#                 print(f"\nResults for query image {i + 1}:")
#                 for match in result["matches"]:
#                     print(
#                         f"  {os.path.basename(match['path'])}: {match['similarity_score']:.4f}"
#                     )

#     except FileNotFoundError as e:
#         print(f"Error: Could not find sample image files - {e}")
#     except Exception as e:
#         print(f"Error during processing: {e}")
