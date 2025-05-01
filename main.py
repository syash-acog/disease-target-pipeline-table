from llm_client import LLMClient
from db_client import DBClient
from extractor import DrugExtractor
import chembl_data
import pandas as pd
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    """
    Main pipeline for extracting drug information from clinical trial data.
    - Loads data for a user-specified disease from the database.
    - Uses an LLM to extract drug names from each trial record.
    - For each extracted drug, fetches ChEMBL information: MoA (short form), target, modality, and approval status.
    - Aggregates results for each trial (NCT ID), handling multiple drugs and multiple targets/MoAs per drug.
    - Writes/updates the results to a CSV file, ensuring each NCT ID is unique.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset", type=int, default=0, help="Start row")
    parser.add_argument("--limit", type=int, default=30, help="Batch size")
    args = parser.parse_args()

    # Prompt user for disease name and fetch relevant data
    disease_name = input("Enter disease name: ").strip().lower()
    logging.info(f"User provided disease: {disease_name}")

    logging.info("Initializing LLM client...")
    llm_client = LLMClient()
    logging.info("Initializing database client...")
    db_client = DBClient()
    logging.info("Fetching data from the database...")
    data = db_client.fetch_data(disease_name)
    logging.info(f"Fetched {len(data)} rows from the database.")

    # Select a batch of rows to process
    batch_data = data[args.offset:args.offset + args.limit]
    logging.info(f"Processing rows {args.offset} to {args.offset + len(batch_data)}.")

    logging.info("Initializing drug extractor...")
    drug_extractor = DrugExtractor(llm_client)
    logging.info("Extracting drug names using LLM...")
    extracted_drugs = drug_extractor.extract_drug_names(batch_data)
    logging.info(f"Extraction complete. Processed {len(extracted_drugs)} rows.")

    # Prepare mappings from NCT ID to extracted/processed fields
    nctid_to_extracted = {
        row["nct_id"]: ", ".join(row["extracted_drugs"]) if isinstance(row["extracted_drugs"], list) else row["extracted_drugs"]
        for row in extracted_drugs
    }
    nctid_to_moa = {}
    nctid_to_target = {}
    nctid_to_moltype = {}
    nctid_to_approval = {}
    nctid_to_moa_short = {}

    # For each trial, process all extracted drugs and aggregate ChEMBL info
    for row in extracted_drugs:
        drug_list = row["extracted_drugs"]
        if isinstance(drug_list, str):
            drug_list = [d.strip() for d in drug_list.split(",") if d.strip()]

        moa_blocks = []
        target_blocks = []
        moltype_blocks = []
        approval_blocks = []
        moa_short_blocks = []

        for drug in drug_list:
            # Fetch ChEMBL IDs for the drug
            chembl_ids = chembl_data.get_chembl_id_exact(drug)
            # Fetch MoA and target info for these IDs
            moa_targets = chembl_data.fetch_moa_targets_for_ids(chembl_ids)
            # Get MoA (full/fallback) and short MoA (symbol: keyword)
            moa_str = chembl_data.get_moa_with_target_fallback(moa_targets)
            moa_blocks.append([s.strip() for s in moa_str.split(";")] if moa_str and moa_str != "NA" else [])
            target_list = [mt[2] for mt in moa_targets if mt[2] and mt[2] != "NA"]
            target_blocks.append(target_list)
            moltype_list = [chembl_data.fetch_molecule_type(cid) for cid in chembl_ids if cid]
            moltype_blocks.append(moltype_list)
            if chembl_ids:
                approval_status = chembl_data.fetch_approval_status(chembl_ids[0], disease_name)
            else:
                approval_status = "NA"
            approval_blocks.append([approval_status])
            moa_short = chembl_data.get_moa_short(moa_targets)
            moa_short_blocks.append(moa_short if moa_short else "NA")

        # Aggregate results for all drugs in the trial
        nctid_to_moa[row["nct_id"]] = chembl_data.format_multi_drug_output(moa_blocks)
        nctid_to_target[row["nct_id"]] = chembl_data.format_multi_drug_output(target_blocks)
        nctid_to_moltype[row["nct_id"]] = chembl_data.format_multi_drug_output(moltype_blocks)
        nctid_to_approval[row["nct_id"]] = chembl_data.format_multi_drug_output(approval_blocks)
        nctid_to_moa_short[row["nct_id"]] = " | ".join(moa_short_blocks)

    # Write results to batch_data for CSV output
    for row in batch_data:
        nct_id = row["nct_id"]
        extracted = nctid_to_extracted.get(nct_id, "")
        if isinstance(extracted, list):
            row["Extracted Drugs"] = ", ".join(extracted)
        else:
            row["Extracted Drugs"] = extracted
        # Only one MoA column, short form
        row["MoA"] = nctid_to_moa_short.get(nct_id, "")
        row["Target"] = nctid_to_target.get(nct_id, "")
        row["Modality"] = nctid_to_moltype.get(nct_id, "")
        row["Approval Status"] = nctid_to_approval.get(nct_id, "")

    # Save or update the output CSV, ensuring unique NCT IDs
    out_file = 'drugs_moa_target_mod.csv'
    if os.path.exists(out_file):
        df_existing = pd.read_csv(out_file)
        # Remove rows with nct_id in current batch (to update them)
        df_existing = df_existing[~df_existing["nct_id"].isin([row["nct_id"] for row in batch_data])]
        df_new = pd.DataFrame(batch_data)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = pd.DataFrame(batch_data)
    df_final.to_csv(out_file, index=False)
    logging.info(f"Saved/updated {len(batch_data)} rows to {out_file}.")

if __name__ == "__main__":
    main()