from flask import Flask, request, jsonify
from flask_cors import CORS
from encode_and_store import setup_database, retrieve_content_by_url, get_embedding_provider
from retrive import load_faiss_index, get_openai_response, retrieve_similar_pages
from consts import EMBEDDING_PROVIDER

app = Flask(__name__)
CORS(app)

# Load FAISS index and setup database connection
index = load_faiss_index()
conn, c = setup_database()
embedding_provider = get_embedding_provider(EMBEDDING_PROVIDER)
model = "gpt-4o"
@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    user_query = data.get('query')
    top_k = data.get('top_k', 5)

    if not user_query:
        return jsonify({"error": "Query parameter is required"}), 400
    print(f"Received query: {user_query}")
    # Retrieve similar pages using the selected provider
    results = retrieve_similar_pages(user_query, embedding_provider, index, c, top_k)

    context_text = "\n".join([f"Title: {title}, Content: {retrieve_content_by_url(url, c)[:5000]}" for url, title in results])
    response = get_openai_response(user_query, context_text, model)
    # import time
    # time.sleep(1)
    # response = "זוהי תגובה כלשהי " * 10
    
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
