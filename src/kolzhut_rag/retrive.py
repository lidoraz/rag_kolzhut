import sqlite3
import faiss
from openai import OpenAI
import os
import numpy as np
import json
from datetime import date
from encode_and_store import setup_database, retrieve_content_by_url, get_embedding_provider
from consts import EMBEDDING_PROVIDER

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

import re


def markdown_to_html(text):
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # Convert \n to <br>
    text = text.replace('\n', '<br>')

    return text




def get_openai_response(user_query, context_text, model):
    print("Getting OpenAI response")
    assert model in ('gpt-4o-mini', 'gpt-4o')
    try:
        # Call GPT-4o-mini
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant helping users with their queries using relevant retrieved context."
                            " Format your responses with appropriate line breaks for better readability."
                            " For reference, today date is <TODAY>{today_date}</TODAY>".format(today_date=date.today())},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {user_query}"}
            ]
        )
        print("Got OpenAI response")
        content = response.choices[0].message.content
        return markdown_to_html(content)
    except Exception as e:
        print(f"Error getting OpenAI response: {e}")
        return "Error: Failed to get response from OpenAI"


def get_openai_embedding(text):
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = response['data'][0]['embedding']
        return embedding
    except Exception as e:
        print(f"Error getting OpenAI embedding: {e}")
        return None

def cosine_similarity(a, b):
    return sum(x*y for x, y in zip(a, b)) / (sum(x**2 for x in a)**0.5 * sum(y**2 for y in b)**0.5)

def get_minilm_embedding(text, model):
    return model.encode([text])[0]

def retrieve_similar_pages(query, embedding_provider, index, c, top_k=10):
    query_embedding = embedding_provider.get_embedding(query)

    if query_embedding is None:
        return []

    query_embedding = np.array(query_embedding).reshape(1, -1)
    distances, indices = index.search(query_embedding, top_k)
    
    idx_tuples = [(int(idx),) for idx in indices[0]]
    c.execute('SELECT url, title FROM metadata WHERE faiss_index IN ({seq})'.format(
        seq=','.join(['?'] * len(idx_tuples))), [x[0] for x in idx_tuples])

    results = c.fetchall()
    return results

def main():
    query = "מהם האחוזים לשעת עבודה ביום שבת?"
    query = "כמה ימים דמי אבטלה מקבלים אחרי גיל 50 ?" # 300
    query = "מה עושים עם הכספים של הפנסיה אחרי שאתה נפטר ולא הספקת לקבל את הכל?"

    top_k = 5

    # Setup database
    conn, c = setup_database()

    # Initialize embedding provider
    embedding_provider = get_embedding_provider(EMBEDDING_PROVIDER)

    # Load FAISS index
    index = load_faiss_index()

    # Retrieve similar pages using the selected provider
    results = retrieve_similar_pages(query, embedding_provider, index, c, top_k)
    
    context_text = "\n".join([f"Title: {title}, Content: {retrieve_content_by_url(url, c)[:5000]}" for url, title in results])
    print("Context text:", context_text)
    response = get_openai_response(query, context_text)
    print(f"OpenAI Response: {response}")

    conn.close()


if __name__ == "__main__":
    main()
