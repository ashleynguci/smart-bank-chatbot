import os
import json
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders import SitemapLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import SoupStrainer
from dotenv import load_dotenv
import time
from typing_extensions import TypedDict, List

# Loading one document takes:
# - From the web: around 0.65 seconds.
# - From the already parsed local file: around 0.0015 seconds.
# So it's over 400 times faster to load from a local file than from the web!

# https://www.nordea.fi/henkiloasiakkaat/tuki/yleiset-ehdot-www-sivujen-kayttoon.html

CHUNK_SIZE = 1000  # Maximum size of a chunk in characters
CHUNK_OVERLAP = 200 # Overlap between chunks in characters

text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

def exclude_footer(tag):
    # Exclude <footer class="footer"> and <div class="nav">, include everything else
    return not (tag == "footer")

# Embeddings need credentials
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

if os.path.exists("docs.json") and os.path.exists("chroma_db"):
  print("""
Looks like you've already loaded the documents from the web and store them in docs.json and chroma_db!\n
If you want to load them again (perhaps with new links), delete docs.json and chroma_db first.\n""")

else:
  print("No existing documents or vector store found. Creating new ones...")
  # Load and process documents
  start_time = time.time()

  # There are 443 relevant English-language pages in the sitemap (related to personal banking).
  # These start with https://www.nordea.fi/en/personal/...
  # So they can be filtered with a Regex filter_urls=["https://.*nordea.fi/en/personal/.*"]
  #
  # Similarly, there are 492 relevant Finnish-language pages in the sitemap (related to personal banking).
  # These start with https://www.nordea.fi/henkiloasiakkaat/...
  # So they can be filtered with a Regex filter_urls=["https://.*nordea.fi/henkiloasiakkaat/.*"]

  # Load sitemap - Does not collect title and description, which are needed for tools
  # webloader = SitemapLoader(
  #   web_path="./data/sitemap.xml", # Locally stored. 
  #   is_local=True,
  #   )

  webloader = WebBaseLoader(
    # TODO: Load links from a separate file instead of hardcoding them (Use the sitemap.xml here?)
    web_paths=(
      "https://www.nordea.fi/henkiloasiakkaat/palvelumme/lainat/opintolaina/opintolainan-korko.html",
      "https://www.nordea.fi/henkiloasiakkaat/palvelumme/lainat/asuntolainat/asuntolaina.html",
      "https://www.nordea.fi/henkiloasiakkaat/sinun-elamasi/koti/ensimmaisen-kodin-ostaminen/",
      "https://www.nordea.fi/en/personal/our-services/online-mobile-services/",
      "https://www.nordea.fi/en/personal/our-services/online-mobile-services/mobile-banking/",
      "https://www.nordea.fi/en/personal/our-services/loans/home-loans/asploan.html",
      "https://www.nordea.fi/en/personal/our-services/savings-investments/savings-accounts/asp-account.html",
      "https://www.nordea.fi/henkiloasiakkaat/sinun-elamasi/turvallisuus/jouduitko-huijatuksi.html"
    ),
    requests_per_second=1
  )
  docs = webloader.load()

  print(docs[0])
  
  # Save documents
  with open("docs.json", "w", encoding="utf-8") as f:
    json.dump([doc.dict() for doc in docs], f, ensure_ascii=False, indent=2)

  # Split documents
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
  all_splits = text_splitter.split_documents(docs)

  # Create and persist vector store
  vector_store = Chroma.from_documents(
    all_splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
  )
  vector_store.persist()

  elapsed = time.time() - start_time

  print(f"\nCreated {len(docs)} documents and {len(all_splits)} document chunks. These have been saved to 'docs.json' and './chroma_db'.")
  print(f"\nLoading documents took {elapsed:.2f} seconds.")
  if len(docs) > 0:
    print(f"Average time per document: {elapsed / len(docs):.4f} seconds.")
