#!/usr/bin/env python3
"""
Initialize ChromaDB with project data.

NEW ARCHITECTURE (2-Stage RAG):
- Stage 1: Build lightweight project_index from epic.csv
- Stage 2: On-demand document loading from project folders

This replaces the old approach of indexing all CSVs upfront.
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
    print("CHROMADB INITIALIZATION")
    print("=" * 80)
    print()
    print("New Architecture: 2-Stage RAG")
    print("  Stage 1: Lightweight project_index (epic metadata)")
    print("  Stage 2: On-demand document loading (TDD, estimation, stories)")
    print()

    # Get settings
    settings = get_settings()

    # Project base path
    base_path = Path("data/raw/projects")

    if not base_path.exists():
        print(f"❌ Error: Project directory not found: {base_path}")
        print("Expected structure:")
        print("  data/raw/projects/epic.csv")
        print("  data/raw/projects/PRJ-XXXXX-name/tdd.docx")
        print("  data/raw/projects/PRJ-XXXXX-name/estimation.xlsx")
        print("  data/raw/projects/PRJ-XXXXX-name/jira_stories.xlsx")
        return 1

    print(f"Project directory: {base_path.absolute()}")
    print(f"ChromaDB location: {settings.chroma_persist_dir}")
    print()

    # Initialize indexer
    indexer = ProjectIndexer.get_instance()

    try:
        # Build index
        print("Scanning projects and building project_index collection...")
        count = await indexer.build_index(base_path)

        print()
        print("=" * 80)
        print(f"✅ SUCCESS: Indexed {count} projects")
        print("=" * 80)
        print()
        print("ChromaDB Collections:")
        print("  - project_index (lightweight metadata)")
        print()
        print("Index ready for hybrid search!")
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
