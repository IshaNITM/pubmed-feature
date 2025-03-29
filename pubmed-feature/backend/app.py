from flask import Flask, request, jsonify, render_template

from backend.fetcher import PubMedFetcher
import os


app = Flask(__name__, 
           template_folder='../frontend/templates', 
           static_folder='../frontend/static')

# Initialize with your API key
fetcher = PubMedFetcher(api_key="f41c8f35f5f1a7ea643e4b54c7423c09df08")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_papers():
    data = request.json
    query = data.get('query')
    max_results = data.get('max_results', 50)
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    try:
        papers = fetcher.fetch_papers(query, max_results)
        return jsonify({"papers": papers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)