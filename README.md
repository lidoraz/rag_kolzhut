# kolzhut_rag/kolzhut_rag/README.md

# kolzhut_rag

## Overview
This project is a web scraping tool designed to collect data from the website [kolzchut.org.il](https://www.kolzchut.org.il). It utilizes Python libraries such as `requests` and `BeautifulSoup` to scrape web pages and save the content to a MongoDB database.

## Features
- Scrapes web pages and extracts titles and content.
- Saves scraped data to MongoDB for easy retrieval and analysis.
- Follows links to scrape additional pages within the specified domain.

## Installation
To install the project dependencies, use Poetry. First, ensure you have Poetry installed, then run:

```bash
poetry install
```

## Usage
To run the scraper, execute the following command:

```bash
poetry run python scrape.py
```

This will start the scraping process from the specified starting URL.

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.