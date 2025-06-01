# Update Chroma DB with new documents without needing to fetch all documents from the web.
# docs*.json files are human-readable and can be edited manually - after editing them, run this script to update the vector database.

import os
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import time

JSON_FILE = "docs_en.json" # Set path to Document JSON file
NEW_DB_DIR = "./chroma_db_en" # Directory to store the updated vector store
CHUNK_SIZE = 1000  # Maximum size of a chunk in characters
CHUNK_OVERLAP = 200 # Overlap between chunks in characters

if not os.path.exists(JSON_FILE):
  raise FileNotFoundError(f"The JSON file {JSON_FILE} does not exist.")

# Embeddings need credentials
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

start_time = time.time()

# Open the JSON file with documents
with open(JSON_FILE, "r", encoding="utf-8") as f:
    docs = [Document(**doc) for doc in json.load(f)]

print(f"Loaded {len(docs)} documents from {JSON_FILE}.\n\n")

# Split documents
text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
all_splits = text_splitter.split_documents(docs)

# Create and persist vector store
vector_store = Chroma.from_documents(
  all_splits,
  embedding=embeddings,
  persist_directory=NEW_DB_DIR
)

elapsed = time.time() - start_time

print(f"\nCreated {len(all_splits)} document chunks. These have been saved to the vector store in '{NEW_DB_DIR}'.")
print(f"\nVector store creation took {elapsed:.2f} seconds.")