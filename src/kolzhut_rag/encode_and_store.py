import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import hashlib


# SQLite setup
def setup_database():
    conn = sqlite3.connect('kolzchut.db')
    c = conn.cursor()
    return conn, c


def create_metadata_table(c):
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            faiss_index INTEGER
        )
    ''')
    c.connection.commit()


def fetch_pages(c):
    c.execute('SELECT url, title, content FROM pages')
    return c.fetchall()


def save_metadata(c, urls, titles):
    for idx, (url, title) in enumerate(zip(urls, titles)):
        c.execute('INSERT INTO metadata (id, url, title, faiss_index) VALUES (?, ?, ?, ?)', (idx, url, title, int(idx)))
    c.connection.commit()


# Function to generate a unique hash for each page
def generate_hash(url):
    return hashlib.md5(url.encode()).hexdigest()


# Load pre-trained SentenceTransformer model suitable for multilingual text including Hebrew
def load_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


# Function to encode text to vectors
def encode_text(model, text):
    return model.encode(text)


# Prepare data for FAISS
def prepare_data(pages, model):
    urls = []
    titles = []
    vectors = []

    for url, title, content in pages:
        urls.append(url)
        titles.append(title)
        vector = encode_text(model, content)
        vectors.append(vector)

    return urls, titles, np.array(vectors)


# Initialize FAISS index
def initialize_faiss_index(vectors):
    d = vectors.shape[1]  # Dimension of the vectors
    index = faiss.IndexFlatL2(d)
    index.add(vectors)
    return index


def save_faiss_index(index, filename='faiss_index.faiss'):
    faiss.write_index(index, filename)


# Retrieve similar pages
def retrieve_similar_pages(query, model, index, c, top_k=5):
    query_vector = encode_text(model, query).reshape(1, -1)
    distances, indices = index.search(query_vector, top_k)
    print(distances, indices)
    idx_tuples = [(int(idx),) for idx in indices[0]]
    c.execute('SELECT url, title FROM metadata WHERE faiss_index IN ({seq})'.format(
        seq=','.join(['?'] * len(idx_tuples))), [x[0] for x in idx_tuples])

    results = c.fetchall()
    return results


# Retrieve content by URL
def retrieve_content_by_url(url, c):
    c.execute('SELECT content FROM pages WHERE url = ?', (url,))
    result = c.fetchone()
    if result:
        return result[0]
    return None


# Main function
def main():
    conn, c = setup_database()
    create_metadata_table(c)

    model = load_model()
    pages = fetch_pages(c)

    urls, titles, vectors = prepare_data(pages, model)
    index = initialize_faiss_index(vectors)

    save_faiss_index(index)
    save_metadata(c, urls, titles)

    conn.close()
    print("Encoding and storing completed.")


if __name__ == "__main__":
    main()