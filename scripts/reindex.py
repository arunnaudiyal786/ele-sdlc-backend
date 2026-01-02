#!/usr/bin/env python3
"""Reindex ChromaDB by deleting and recreating all collections."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.base.config import get_settings
from app.rag.vector_store import ChromaVectorStore


async def main():
    """Delete all collections and reinitialize."""
    settings = get_settings()

    print(f"Reindexing ChromaDB at {settings.chroma_persist_dir}")
    vector_store = ChromaVectorStore.initialize(settings.chroma_persist_dir)

    collections = ["epics", "estimations", "tdds", "stories", "gitlab_code"]
    for name in collections:
        print(f"Deleting collection: {name}")
        await vector_store.delete_collection(name)

    print("Collections deleted. Run init_vector_db.py to repopulate.")


if __name__ == "__main__":
    asyncio.run(main())
