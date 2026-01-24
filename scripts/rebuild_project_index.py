#!/usr/bin/env python3
"""
Rebuild Project Index

Scans data/raw/projects/ and builds ChromaDB index with project metadata.
Replaces old CSV-based indexing with on-demand document retrieval.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.project_indexer import ProjectIndexer
from app.components.base.config import get_settings


async def main():
    """Build project index from data/raw/projects/"""
    print("=" * 80)
    print("PROJECT INDEX REBUILD")
    print("=" * 80)

    # Get settings
    settings = get_settings()

    # Project base path
    base_path = Path("data/raw/projects")

    if not base_path.exists():
        print(f"\n❌ Error: Project directory not found: {base_path}")
        print("Please ensure data/raw/projects/ exists with project folders")
        return 1

    print(f"\nProject directory: {base_path.absolute()}")
    print(f"ChromaDB location: {settings.chroma_persist_dir}")
    print()

    # Initialize indexer
    indexer = ProjectIndexer.get_instance()

    try:
        # Build index
        print("Scanning projects and building index...")
        count = await indexer.build_index(base_path)

        print()
        print("=" * 80)
        print(f"✅ SUCCESS: Indexed {count} projects")
        print("=" * 80)
        print()
        print("Index ready for hybrid search!")
        print("Collection: project_index")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ ERROR: Index build failed")
        print("=" * 80)
        print(f"\n{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
