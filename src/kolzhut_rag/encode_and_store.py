import sqlite3
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import hashlib
import json
import os
from tqdm import tqdm
from openai import OpenAI
from kolzhut_rag.consts import EMBEDDING_PROVIDER


# SQLite setup
def setup_database():
    conn = sqlite3.connect('kolzchut.db', check_same_thread=False)
    c = conn.cursor()
    return conn, c


def create_metadata_table(c):
    print("Dropping and creating metadata table...")
    c.execute('DROP TABLE IF EXISTS metadata')
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            faiss_index INTEGER
        )
    ''')
    c.connection.commit()


def fetch_pages(c, limit=None):
    word_limit = 4000 #5465
    if limit:
        c.execute('SELECT url, title, content FROM pages where word_count < ? LIMIT ?', (word_limit, limit,))
    else:
        c.execute('SELECT url, title, content FROM pages where word_count < ? ', (word_limit,))
    return c.fetchall()


def save_metadata(c, urls, titles):
    for idx, (url, title) in enumerate(zip(urls, titles)):
        c.execute('INSERT INTO metadata (id, url, title, faiss_index) VALUES (?, ?, ?, ?)', (idx, url, title, int(idx)))
    c.connection.commit()


# Function to generate a unique hash for each page
def generate_hash(url):
    return hashlib.md5(url.encode()).hexdigest()


class BaseEmbeddingProvider:
    def get_embedding(self, text):
        raise NotImplementedError("Subclasses should implement this method")

    def get_average_embedding(self, text, max_words=1200): #
        words = text.split()
        if len(words) <= max_words:
            print(len(words))
            return self.get_embedding(text)
        
        print(f"Text too long ({len(words)} words), splitting into parts...")
        parts = [words[i:i + max_words] for i in range(0, len(words), max_words)]
        embeddings = [self.get_embedding(' '.join(part)) for part in parts]
        return np.mean(embeddings, axis=0)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.client = OpenAI(api_key=self.get_openai_api_key())

    def get_openai_api_key(self):
        try:
            with open(os.path.expanduser("~/.ssh/creds_postgres.json")) as f:
                creds = json.load(f)
            print("API key loaded successfully")
            return creds["OPENAI_TOKEN"]
        except Exception as e:
            print(f"Error loading API key: {e}")
            return None

    def get_embedding(self, text):
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-large", # text-embedding-ada-002",
                input=text
            )
            embedding = np.array(response.data[0].embedding)
            return embedding
        except Exception as e:
            print(f"Error getting OpenAI embedding: {e}")
            return None


class MiniLMEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def get_embedding(self, text):
        return self.model.encode([text])[0]


def get_embedding_provider(provider_name):
    if provider_name == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_name == "minilm":
        return MiniLMEmbeddingProvider()
    else:
        raise ValueError("Unsupported embedding provider")


# Prepare data for FAISS
def prepare_data(pages, model):
    urls = []
    titles = []
    vectors = []

    for url, title, content in tqdm(pages, desc="Encoding pages"):
        vector = model.get_average_embedding(content)
        if vector is None:
            print(f"Error: Failed to get embedding for {url}, word_count: {len(content.split())}")
            continue
        urls.append(url)
        titles.append(title)
        vectors.append(vector)

    return urls, titles, np.array(vectors)


# Initialize FAISS index
def initialize_faiss_index(vectors):
    d = vectors.shape[1]  # Dimension of the vectors
    # TODO: Switch to Cosine similarity as it is more suitable for embeddings, must normalize vectors first
    index = faiss.IndexFlatL2(d)
    index.add(vectors)
    return index


def save_faiss_index(index, filename='faiss_index.faiss'):
    faiss.write_index(index, filename)


# Retrieve similar pages
def retrieve_similar_pages(query, model, index, c, top_k=5):
    query_vector = model.encode(query).reshape(1, -1)
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


def store_page_content(url, title, content, embedding_provider, c):
    embedding = embedding_provider.get_embedding(content)

    if embedding is None:
        print(f"Error: Failed to get embedding for {url}")
        return

    c.execute("INSERT INTO pages (url, title, content, embedding) VALUES (?, ?, ?, ?)",
              (url, title, content, json.dumps(embedding)))


# Main function
def main():
    conn, c = setup_database()
    create_metadata_table(c)

    embedding_provider = get_embedding_provider(EMBEDDING_PROVIDER)
    limit = 300
    pages = fetch_pages(c, limit)

    urls, titles, vectors = prepare_data(pages, embedding_provider)
    index = initialize_faiss_index(vectors)

    save_faiss_index(index)
    save_metadata(c, urls, titles)

    conn.close()
    print("Encoding and storing completed.")


if __name__ == "__main__":
    main()