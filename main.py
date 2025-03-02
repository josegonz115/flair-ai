# from flask import Flask, jsonify, request
# import requests
# from bs4 import BeautifulSoup
# import re
# import os

# app = Flask(__name__)
# url = "https://pinterest.com/"

# @app.after_request
# def after_request(response):
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
#     return response

# @app.route("/")
# def home():
#     return jsonify({
#         "message": "Pinterest Scraper By Kurizu",
#         "routes": {
#             "Info": f"{request.url_root}api/<username>/<board_name>/info",
#             "Pins": f"{request.url_root}api/<username>/<board_name>/pins",
#         }
#     })

# @app.route("/api/<username>/<board_name>/info")
# def board_info(username, board_name):
#     response = requests.get(f"{url}{username}/{board_name}")
#     soup = BeautifulSoup(response.text, 'html.parser')
    
#     title = soup.find("h1").text
#     count_element = soup.find("header").find('div', {'data-test-id': 'board-count-info'})
#     count = int(re.sub(r'\D', '', count_element.text)) if count_element else 0
    
#     return jsonify({
#         "title": title,
#         "totalPins": count
#     })

# @app.route("/api/<username>/<board_name>/pins")
# def board_pins(username, board_name):
#     # Get quality parameter from URL (default to highest)
#     quality = request.args.get('quality', 'original')
    
#     response = requests.get(f"{url}{username}/{board_name}")
#     soup = BeautifulSoup(response.text, 'html.parser')
    
#     results = []
#     for i, img in enumerate(soup.find_all("img")):
#         src = img.get("src")
#         alt = img.get("alt")
#         if src:
#             # good balance of detail and memory efficiency
#             src = re.sub(r'/\d+x/', '/736x/', src) 
#             results.append({"src": src, "alt": alt})
    
#     return jsonify({"images": results})

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 3000))
#     print(f"PORT {port}")
#     app.run(host='0.0.0.0', port=port)


