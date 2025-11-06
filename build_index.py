#!/usr/bin/env python3
"""
Build the destination index from JSON files in data/destinations/
"""
from src.build_index import DestinationIndex

if __name__ == "__main__":
    print("Building destination index...")
    index = DestinationIndex()
    index.build_index()
    print("Done!")

