import sqlite3
import faiss
from openai import OpenAI
import os
import json
from encode_and_store import load_model, setup_database, retrieve_similar_pages, retrieve_content_by_url


def load_faiss_index(filename='faiss_index.faiss'):
    return faiss.read_index(filename)


def get_openai_api_key():
    try:
        with open(os.path.expanduser("~/.ssh/creds_postgres.json")) as f:
            creds = json.load(f)
        print("API key loaded successfully")
        return creds["OPENAI_TOKEN"]
    except Exception as e:
        print(f"Error loading API key: {e}")
        return None



client = OpenAI(api_key=get_openai_api_key())

def get_openai_response(user_query, context_text):
    try:
        # Call GPT-4o-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant helping users with their queries using relevant retrieved context."},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {user_query}"}
            ]
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting OpenAI response: {e}")
        return "Error: Failed to get response from OpenAI"


def main():
    query = "מהם האחוזים לשעת עבודה ביום שבת?"
    # query = "פינוי דייר מהדירה באמצע חוזה השכירות"
    # query = "איפה ניתן לבצע את הבחירות ברשות המקומית?"
    top_k = 10

    # Load model
    model = load_model()

    # Setup database
    conn, c = setup_database()

    # Load FAISS index
    index = load_faiss_index()

    # Retrieve similar pages
    results = retrieve_similar_pages(query, model, index, c, top_k)
    # context = ""
    for url, title in results:
        content = retrieve_content_by_url(url, c)
        # context += f"Title: {title}, Content: {content[:200]}...\n"  # Collect context from top results
    context_text = "\n".join([f"Title: {title}, Content: {content[:5000]}" for url, title in results])
    print("Context text:", context_text)
    response = get_openai_response(query, context_text)
    print(f"OpenAI Response: {response}")

    conn.close()


if __name__ == "__main__":
    main()
