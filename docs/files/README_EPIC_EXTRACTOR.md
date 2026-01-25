# Epic Information Extractor

A Python script to extract epic-level information from project folders and their TDD documents.

## Overview

This script traverses the `data/projects/` directory and extracts epic information from each project:
- **Epic ID**: Extracted from folder name (e.g., `PRJ-10051`)
- **Epic Title**: Human-readable title derived from folder name (e.g., "Inventory Sync Automation")
- **Epic Description**: Purpose/description extracted from the TDD document

## Prerequisites

```bash
pip install python-docx
```

## Usage

### Basic Usage

Run the script from the project root:

```bash
python extract_epic_info.py
```

This will:
1. Scan all folders in `data/projects/`
2. Extract epic information from each project
3. Generate `epic.csv` in `ele-sdlc-backend/data/raw/projects/` with all epic records

### Output Format

The generated CSV file contains three columns:

| Column | Description | Example |
|--------|-------------|---------|
| `epicid` | Project identifier | PRJ-10051 |
| `epic_title` | Human-readable title | Inventory Sync Automation |
| `epic_description` | Purpose from TDD | This document describes the technical design for... |

### Example Output

The CSV file is saved to: `ele-sdlc-backend/data/raw/projects/epic.csv`

```csv
epicid,epic_title,epic_description
PRJ-10051,Inventory Sync Automation,This document describes the technical design for automating inventory synchronization...
PRJ-10052,Order Fulfillment Optimization,This document describes the technical design for optimizing the order fulfillment process...
```

## Directory Structure

The script expects the following structure:

```
data/projects/
├── PRJ-10051-inventory-sync-automation/
│   ├── tdd.docx
│   ├── estimation.xlsx
│   └── jira_stories.xlsx
├── PRJ-10052-order-fulfillment-optimization/
│   ├── tdd.docx
│   ├── estimation.xlsx
│   └── jira_stories.xlsx
└── ...
```

## How It Works

1. **Folder Name Parsing**: Extracts epic ID and title from folder names following the pattern `{EPICID}-{title-slug}`
2. **TDD Parsing**: Uses python-docx to read `tdd.docx` files
3. **Purpose Extraction**: Locates the "Purpose" section (typically section 1.1) and extracts the description
4. **CSV Generation**: Writes all extracted data to `epic_data.csv`

## Customization

### Change Output Filename

Edit the `save_to_csv()` call in the `main()` function:

```python
extractor.save_to_csv("custom_epic.csv")  # Still saves to ele-sdlc-backend/data/raw/projects/
```

### Change Output Directory

Edit the `EpicExtractor()` initialization:

```python
extractor = EpicExtractor(
    projects_dir="data/projects",
    output_dir="custom/output/path"
)
```

### Change Projects Directory

```python
extractor = EpicExtractor(projects_dir="path/to/projects")
```

## Troubleshooting

### "Projects directory not found"
- Ensure you're running the script from the correct directory
- Verify that `data/projects/` exists

### "TDD document not found"
- The script will log this but continue processing other projects
- Check that each project folder contains `tdd.docx`

### "No description found in TDD"
- The TDD may not have a "Purpose" section
- The script uses fallback logic to find the first meaningful paragraph

## Script Details

- **Language**: Python 3.7+
- **Dependencies**: python-docx
- **Input**: Project folders with TDD documents
- **Output**: CSV file with epic information
- **Error Handling**: Continues processing even if individual projects fail
