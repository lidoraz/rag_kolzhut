import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import hashlib
import sqlite3

# SQLite setup
conn = sqlite3.connect('kolzchut.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY,
        url TEXT,
        title TEXT,
        content TEXT,
        word_count INTEGER
    )
''')
conn.commit()


# Function to generate a unique hash for each page
def generate_hash(url):
    return hashlib.md5(url.encode()).hexdigest()


# Function to save page content to SQLite
def save_to_db(url, title, content):
    page_hash = generate_hash(url)
    word_count = len(content.split())
    c.execute('''
        INSERT OR REPLACE INTO pages (id, url, title, content, word_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (page_hash, url, title, content, word_count))
    conn.commit()


# Function to scrape a page
def scrape_page(base_url, url, visited, depth, max_depth=2):
    if url in visited or depth > max_depth:
        return

    full_url = urljoin(base_url, url)
    human_readable_url = unquote(full_url)
    print(f"Scraping: {human_readable_url}")

    response = requests.get(full_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    article = soup.find('article', {'id': 'bodyContent', 'role': 'main'})
    if article:
        print("Found article")
        portal_boxes = article.find('div', {'class': 'portal-boxes-table'})
        if portal_boxes:
            print("Found portal boxes")
            links_to_scrape = portal_boxes.find_all('a', href=True)
            for link in links_to_scrape:
                link_url = link['href']
                if link_url.startswith("/he/"):
                    scrape_page(base_url, link_url, visited, depth + 1)
        else:
            print("No portal boxes found, scraping content")
            content_div = article.find('div', {'class': 'mw-parser-output'})
            if content_div:
                content = content_div.get_text(separator=' ', strip=True)
                title = soup.find('title').text.strip()
                save_to_db(full_url, title, content)
            else:
                print("No content div found")
    else:
        print("No article found")
        content = soup.get_text(separator=' ', strip=True)
        title = soup.find('title').text.strip()
        save_to_db(full_url, title, content)

    visited.add(url)

    # Find and scrape all linked pages
    if depth < max_depth and not portal_boxes:
        links_to_scrape = article.find_all('a', href=True) if article else soup.find_all('a', href=True)
        for link in links_to_scrape:
            link_url = link['href']
            if link_url.startswith("/he/"):
                scrape_page(base_url, link_url, visited, depth + 1)


# Main scraping function
def main():
    base_url = "https://www.kolzchut.org.il/he/%D7%A2%D7%9E%D7%95%D7%93_%D7%A8%D7%90%D7%A9%D7%99"
    start_url = "/he/%D7%A2%D7%9E%D7%95%D7%93_%D7%A8%D7%90%D7%A9%D7%99"
    visited = set()
    max_depth = 2
    print("Starting scrape...")
    scrape_page(base_url, start_url, visited, depth=0, max_depth=max_depth)
    print(f"Scraped {len(visited)} pages.")


if __name__ == "__main__":
    main()