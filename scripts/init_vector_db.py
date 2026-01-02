#!/usr/bin/env python3
"""Initialize ChromaDB with data from CSV/JSON files."""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json
from app.components.base.config import get_settings
from app.rag.vector_store import ChromaVectorStore
from app.rag.embeddings import OllamaEmbeddingService


async def load_and_index_epics(vector_store: ChromaVectorStore, embedder: OllamaEmbeddingService, data_path: Path):
    """Load epics.csv and index to ChromaDB."""
    csv_path = data_path / "epics.csv"
    if not csv_path.exists():
        print(f"Skipping epics: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        # Use actual column names from CSV: epic_name, req_description
        text = f"{row.get('epic_name', '')} {row.get('req_description', '')}"
        documents.append({
            "id": str(row.get("epic_id", "")),
            "text": text,
            "metadata": {
                "epic_id": str(row.get("epic_id", "")),
                "epic_name": row.get("epic_name", ""),
                "status": row.get("status", ""),
                "priority": row.get("epic_priority", ""),
                "team": row.get("epic_team", ""),
            },
        })

    if documents:
        embeddings = await embedder.embed_batch([d["text"] for d in documents])
        await vector_store.add_documents("epics", documents, embeddings)
        print(f"Indexed {len(documents)} epics")


async def load_and_index_estimations(vector_store: ChromaVectorStore, embedder: OllamaEmbeddingService, data_path: Path):
    """Load estimations.csv and index to ChromaDB."""
    csv_path = data_path / "estimations.csv"
    if not csv_path.exists():
        print(f"Skipping estimations: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        # Use actual column names: task_description (no tdd_description in estimations)
        text = f"{row.get('task_description', '')}"
        documents.append({
            "id": str(row.get("dev_est_id", "")),
            "text": text,
            "metadata": {
                "estimation_id": str(row.get("dev_est_id", "")),
                "epic_id": str(row.get("epic_id", "")),
                "dev_hours": int(row.get("dev_effort_hours", 0)) if pd.notna(row.get("dev_effort_hours")) else 0,
                "qa_hours": int(row.get("qa_effort_hours", 0)) if pd.notna(row.get("qa_effort_hours")) else 0,
                "complexity": row.get("complexity", ""),
            },
        })

    if documents:
        embeddings = await embedder.embed_batch([d["text"] for d in documents])
        await vector_store.add_documents("estimations", documents, embeddings)
        print(f"Indexed {len(documents)} estimations")


async def load_and_index_tdds(vector_store: ChromaVectorStore, embedder: OllamaEmbeddingService, data_path: Path):
    """Load tdds.csv and index to ChromaDB."""
    csv_path = data_path / "tdds.csv"
    if not csv_path.exists():
        print(f"Skipping tdds: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        # Use actual column names: tdd_name, tdd_description, technical_components
        text = f"{row.get('tdd_name', '')} {row.get('tdd_description', '')}"
        documents.append({
            "id": str(row.get("tdd_id", "")),
            "text": text,
            "metadata": {
                "tdd_id": str(row.get("tdd_id", "")),
                "epic_id": str(row.get("epic_id", "")),
                "technologies": row.get("technical_components", ""),
            },
        })

    if documents:
        embeddings = await embedder.embed_batch([d["text"] for d in documents])
        await vector_store.add_documents("tdds", documents, embeddings)
        print(f"Indexed {len(documents)} TDD sections")


async def load_and_index_stories(vector_store: ChromaVectorStore, embedder: OllamaEmbeddingService, data_path: Path):
    """Load stories_tasks.csv and index to ChromaDB."""
    csv_path = data_path / "stories_tasks.csv"
    if not csv_path.exists():
        print(f"Skipping stories: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        # Use actual column names: jira_story_id, summary, issue_type
        text = f"{row.get('summary', '')} {row.get('acceptance_criteria', '')}"
        documents.append({
            "id": str(row.get("jira_story_id", "")),
            "text": text,
            "metadata": {
                "story_id": str(row.get("jira_story_id", "")),
                "epic_id": str(row.get("epic_id", "")),
                "story_type": row.get("issue_type", ""),
                "story_points": int(row.get("story_points", 0)) if pd.notna(row.get("story_points")) else 0,
            },
        })

    if documents:
        embeddings = await embedder.embed_batch([d["text"] for d in documents])
        await vector_store.add_documents("stories", documents, embeddings)
        print(f"Indexed {len(documents)} stories")


async def load_and_index_gitlab_code(vector_store: ChromaVectorStore, embedder: OllamaEmbeddingService, data_path: Path):
    """Load gitlab_code.json and index to ChromaDB."""
    json_path = data_path / "gitlab_code.json"
    if not json_path.exists():
        print(f"Skipping gitlab_code: {json_path} not found")
        return

    with open(json_path) as f:
        data = json.load(f)

    documents = []
    for item in data:
        # Handle functions_defined as list - join if it's a list
        functions = item.get('functions_defined', [])
        functions_str = ', '.join(functions) if isinstance(functions, list) else str(functions)
        text = f"{item.get('code_block_description', '')} {functions_str}"
        documents.append({
            "id": str(item.get("chg_id", "")),
            "text": text,
            "metadata": {
                "code_id": str(item.get("chg_id", "")),
                "story_id": str(item.get("jira_story_id", "")),
                "repo": item.get("gitlab_repo", ""),
                "language": item.get("code_language", ""),
            },
        })

    if documents:
        embeddings = await embedder.embed_batch([d["text"] for d in documents])
        await vector_store.add_documents("gitlab_code", documents, embeddings)
        print(f"Indexed {len(documents)} code blocks")


async def main():
    """Main initialization routine."""
    settings = get_settings()
    data_path = Path(settings.data_raw_path)

    print(f"Initializing ChromaDB at {settings.chroma_persist_dir}")
    vector_store = ChromaVectorStore.initialize(settings.chroma_persist_dir)
    embedder = OllamaEmbeddingService()

    print(f"Loading data from {data_path}")

    await load_and_index_epics(vector_store, embedder, data_path)
    await load_and_index_estimations(vector_store, embedder, data_path)
    await load_and_index_tdds(vector_store, embedder, data_path)
    await load_and_index_stories(vector_store, embedder, data_path)
    await load_and_index_gitlab_code(vector_store, embedder, data_path)

    print("Initialization complete!")
    print(f"Collections: {vector_store.list_collections()}")


if __name__ == "__main__":
    asyncio.run(main())
