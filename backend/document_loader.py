import os
import json
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import SitemapLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import SoupStrainer, BeautifulSoup
from dotenv import load_dotenv
import time
from typing import Optional
import xml.etree.ElementTree as ET

# Loading one document takes:
# - From the web: around 0.65 seconds.
# - From the already parsed local file: around 0.0015 seconds.
# So it's over 400 times faster to load from a local file than from the web!

# https://www.nordea.fi/henkiloasiakkaat/tuki/yleiset-ehdot-www-sivujen-kayttoon.html

CHUNK_SIZE = 1000  # Maximum size of a chunk in characters
CHUNK_OVERLAP = 200 # Overlap between chunks in characters

# Embeddings need credentials
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

def extract_urls_from_local_sitemap(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = [elem.text for elem in root.findall('.//ns:loc', namespace)]
    # Filter URLs to only include those related to personal banking.
    # urls = [url for url in urls if url.startswith("https://www.nordea.fi/en/personal/") or url.startswith("https://www.nordea.fi/henkiloasiakkaat/")]
    return urls

sitemap_file = './data/sitemap_example.xml' # Local file with the sitemap.

if not os.path.exists(sitemap_file):
  raise FileNotFoundError(f"The Sitemap file {sitemap_file} does not exist. You can get it from https://www.nordea.fi/sitemap.xml")

web_paths = extract_urls_from_local_sitemap(sitemap_file)

def extract_between_markers(text, start_marker, end_marker):
    start_index = text.find(start_marker)
    end_index = text.rfind(end_marker)
    if start_index != -1 and end_index != -1 and start_index < end_index:
        return text[start_index + len(start_marker):end_index]
    return text

if os.path.exists("docs.json") and os.path.exists("chroma_db"):
  print("""
Looks like you've already loaded the documents from the web and store them in docs.json and chroma_db!\n
If you want to load them again (perhaps with new links), delete docs.json and chroma_db first, or give these different names.\n""")

else:
  print(f"No existing documents or vector store found. Getting ready to load {len(web_paths)} documents from the web.\n")
  # Load and process documents
  start_time = time.time()

  # There are 443 relevant English-language pages in the sitemap (related to personal banking).
  # These start with https://www.nordea.fi/en/personal/...
  # So they can be filtered with a Regex filter_urls=["https://.*nordea.fi/en/personal/.*"]
  #
  # Similarly, there are 492 relevant Finnish-language pages in the sitemap (related to personal banking).
  # These start with https://www.nordea.fi/henkiloasiakkaat/...
  # So they can be filtered with a Regex filter_urls=["https://.*nordea.fi/henkiloasiakkaat/.*"]

  def remove_navigation_divs(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for nav_div in soup.find_all("div", attrs={"role": "navigation"}):
        nav_div.decompose()
    return str(soup)

  webloader = WebBaseLoader(
    web_paths=web_paths,
    requests_per_second=1,
    show_progress=True,
  )
  docs = webloader.load()

  for doc in docs:
    if doc.metadata["language"] == "fi-FI": # "en-FI" for English, "fi-FI" for Finnish
      # Meaningful content in Finnish pages is between instances of "Asiakas- palvelu" and "Jaa tämä sivu"
      doc.page_content = extract_between_markers(doc.page_content, "Asiakas- palvelu", "Jaa tämä sivu")
    else:
      # In English pages, the content is between "SearchSuomiSvenskaEnglish" and "Share this page".
      doc.page_content = extract_between_markers(doc.page_content, "SearchSuomiSvenskaEnglish", "Share this page")
  
  # Save documents
  with open("docs.json", "w", encoding="utf-8") as f:
    json.dump([doc.model_dump() for doc in docs], f, ensure_ascii=False, indent=2)

  # Split documents
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
  all_splits = text_splitter.split_documents(docs)

  # Create and persist vector store
  vector_store = Chroma.from_documents(
    all_splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
  )
  #vector_store.persist()

  elapsed = time.time() - start_time

  print(f"\nCreated {len(docs)} documents and {len(all_splits)} document chunks. These have been saved to 'docs.json' and './chroma_db'.")
  print(f"\nLoading documents took {elapsed:.2f} seconds.")
  if len(docs) > 0:
    print(f"Average time per document: {elapsed / len(docs):.2f} seconds.")
