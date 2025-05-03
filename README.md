# Disease/Target Dossier Pipelines Tables

This repository contains two modular pipelines for extracting, cleaning, and integrating drug, target, and clinical trial information from ChEMBL and the AACT clinical trials database.  
It supports both **disease-centric** (disease dossier) and **target-centric** (target dossier) workflows.

---

## Table of Contents

- [Overview](#overview)
- [Folder Structure](#folder-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Disease Dossier Pipeline](#disease-dossier-pipeline)
- [Target Dossier Pipeline](#target-dossier-pipeline)
- [LLM Integration](#llm-integration)
- [Custom Drug Extraction](#custom-drug-extraction)
- [Extending/Customizing](#extendingcustomizing)
- [Troubleshooting](#troubleshooting)
- [Scope for Improvement](#scope-for-improvement)

---

## Overview

- **Disease Dossier:**  
  Given a disease/condition, extract all relevant clinical trials, clean and normalize drug names using an LLM, and annotate each drug with ChEMBL mechanism-of-action, target, modality, and approval status.

- **Target Dossier:**  
  Given a target (gene symbol or ChEMBL target ID), extract all drugs acting on that target, their indications, and all associated clinical trials, with full annotation as above.

---

## Folder Structure

```
clinical_trials_drug_extractor/
│
├── disease_pipeline/
│   ├── disease_main.py
│   ├── chembl_data_disease.py
│   ├── disease_db_client.py
│   ├── extractor.py
│   ├── llm_client.py
│
├── target_pipeline/
│   ├── target_main.py
│   ├── chembl_data_target.py
│   ├── target_db_client.py
│
├── requirements.txt
├── demo.env
└── README.md
```

---

## Setup & Installation

1. **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd disease-target-pipeline-table
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure environment variables:**
    - Copy `demo.env` to `.env` and fill in your database and LLM credentials:
      ```
      cp demo.env .env
      ```
    - Edit `.env` with your values for:
      - `db_host`, `db_port`, `db_userid`, `db_password`
      - `username`, `password` (for LLM API)
      - `base_url` (for LLM API, if not default)

---

## Environment Variables

All sensitive credentials are loaded from `.env`.  
**Example:**
```
db_host=your_db_host
db_port=5432
db_userid=your_user
db_password=your_password

username=your_llm_username
password=your_llm_password
base_url=https://ollama.own1.aganitha.ai
```

---

## Disease Dossier Pipeline

**Purpose:**  
Extracts and annotates all drugs and their mechanisms for a given disease/condition from clinical trials.

**Run the pipeline:**
```bash
cd disease_pipeline
python disease_main.py --offset 0 --limit 100
```
- You will be prompted for a disease name (e.g., `asthma`).
- Output: `drugs_moa_target_mod.csv` with columns:
    - `nct_id`, `Extracted Drugs`, `MoA`, `Target`, `Modality`, `Approval Status`, and trial metadata.

**Approach:**
- Fetches all interventional trials for the disease from AACT.
- Uses an LLM (via `llm_client.py`) to extract and clean core drug names from intervention text.
- For each drug, queries ChEMBL for:
    - ChEMBL ID (with synonym/partial match fallback)
    - Mechanism of action (MoA, short form: `GENE_SYMBOL: keyword`)
    - Target gene/protein
    - Modality (e.g., small molecule, antibody)
    - Approval status for the disease/indication
- Aggregates all info per trial, handling multiple drugs/targets per trial.

---

## Target Dossier Pipeline

**Purpose:**  
Extracts all drugs, indications, and clinical trials for a given target (gene/protein).

**Run the pipeline:**
```bash
cd target_pipeline
python target_main.py --target TUBB4B --output target_pipeline.csv
```
- Replace `TUBB4B` with your gene symbol or ChEMBL target ID.
- Output: `target_pipeline.csv` with columns:
    - `Target Symbol`, `Drug Name`, `MoA`, `Indication`, `Approval Status`, `Modality`, `nct_id`, `phase`, `overall_status`, `sponsor`, `source_class`, `official_title`, `intervention_types`

**Approach:**
- Resolves the target symbol to ChEMBL target ID.
- Finds all drugs acting on this target (from ChEMBL).
- For each drug, fetches all indications (diseases) and approval status.
- For each drug-indication pair, fetches all matching clinical trials from AACT.
- Aggregates all info into a single table.

---

## LLM Integration

- The LLM is used for:
    - Drug name extraction/cleaning from free-text intervention fields.
- LLM API credentials and endpoint are set in `.env`.
- The LLM model can be changed in `llm_client.py`.

---

## Custom Drug Extraction

- The extraction logic is in `extractor.py` (disease pipeline).
- Prompt is highly customized for biomedical context, with explicit rules and examples.
- You can further tune the prompt or add more examples for your use case.

---

## Extending/Customizing

- **Add more columns:**  
  Edit the SQL queries or ChEMBL API calls to fetch additional metadata.
- **Change output format:**  
  Use pandas to write to Excel, Parquet, etc.
- **Improve LLM prompts:**  
  Edit the prompt in `extractor.py`.

---

## Troubleshooting

- **500 Server Error from LLM:**  
  The LLM API may be down or overloaded.
- **No drugs/targets found:**  
  Check your input spelling, or try a more common disease/target, if not any then api problem.
- **Database connection errors:**  
  Ensure your `.env` is correct and the database is accessible from your machine.
- **Missing trial rows for some indications:**  
  See "Scope for Improvement" below.

---

## Scope for Improvement

- **Indication-Condition Matching (LLM):**
    - Currently, the pipeline matches ChEMBL indication names to AACT condition names using string matching.
    - For improved recall and accuracy, you can use an LLM to match ChEMBL indications to the best AACT condition name, handling synonyms and phrasing differences.
    - Integrate this step before querying trials for a drug-indication pair to reduce missing data due to naming mismatches.


