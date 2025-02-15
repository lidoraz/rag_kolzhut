from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from kolzhut_rag.encode_and_store import setup_database, retrieve_content_by_url, get_embedding_provider
from kolzhut_rag.retrive import load_faiss_index, get_openai_response, retrieve_similar_pages, \
    markdown_to_html  # , retrieve_similar_pages_cosine
from kolzhut_rag.consts import EMBEDDING_PROVIDER

app = Flask(__name__)
CORS(app)

# Rate limiter setup
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Load FAISS index and setup database connection
index = load_faiss_index()
conn, c = setup_database()
embedding_provider = get_embedding_provider(EMBEDDING_PROVIDER)
model = "gpt-4o-mini"


@app.route('/api/query', methods=['POST'])
@limiter.limit("10 per minute")  # Limit to 10 requests per minute per IP
def query():
    data = request.json
    user_query = data.get('query')
    top_k = 5  # Set top_k internally

    if not user_query:
        return jsonify({"error": "Query parameter is required"}), 400

    print(f"Received query: {user_query}")
    # Retrieve similar pages using the selected provider with cosine similarity
    results = retrieve_similar_pages(user_query, embedding_provider, index, c, top_k)

    context_text = "\n".join(
        [f"Title: {title}, Content: {retrieve_content_by_url(url, c)[:5000]}" for url, title in results])
    # context_text = ""
    res = get_openai_response(user_query, context_text, model, stream=True)
    def generate():
        for chunk in res:
            content_delta = chunk.choices[0].delta.content
            # print(content_delta)
            if content_delta:
                yield content_delta.encode('utf-8')  # Encode chunk to bytes


    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
