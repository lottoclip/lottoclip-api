
import sys
import os

# Add project root to sys.path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import LottoCrawler

def regenerate():
    print("Regenerating store index...")
    crawler = LottoCrawler()
    crawler.update_store_index_file()
    print("Done.")

if __name__ == "__main__":
    regenerate()
