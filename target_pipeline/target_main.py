"""
Main pipeline for extracting drug and indication information for a user-specified target.
- Loads data for a user-specified target (gene symbol or ChEMBL target ID).
- Finds all drugs acting on this target using ChEMBL.
- For each drug, fetches indications, MoA (short form), modality, approval status, and trial information.
- Aggregates results for each drug–indication pair.
- Writes/updates the results to a CSV file.
"""

import chembl_data_target
import pandas as pd
import logging
import os
from target_db_client import TargetDBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=str, required=True, help="Target gene symbol or ChEMBL target ID")
    parser.add_argument("--output", type=str, default="target_pipeline.csv", help="Output CSV file")
    args = parser.parse_args()

    target_input = args.target.strip()
    logging.info(f"User provided target: {target_input}")

    # Get ChEMBL target ID if user gave a gene symbol
    target_chembl_id = chembl_data_target.get_target_chembl_id(target_input)
    if not target_chembl_id:
        logging.error(f"Could not find ChEMBL target ID for: {target_input}")
        return

    logging.info(f"Using ChEMBL target ID: {target_chembl_id}")

    # Get all drugs for this target
    drugs = chembl_data_target.get_drugs_for_target(target_chembl_id)
    if not drugs:
        logging.warning(f"No drugs found for target {target_chembl_id}")
        return

    logging.info(f"Found {len(drugs)} drugs for target {target_chembl_id}")

    # Initialize DB client
    db_client = TargetDBClient()

    # For each drug, get indications, MoA, modality, approval status, and trial info
    results = []
    for drug in drugs:
        chembl_id = drug["molecule_chembl_id"]
        drug_name = drug.get("pref_name") or chembl_id
        modality = chembl_data_target.fetch_molecule_type(chembl_id)
        moa_targets = chembl_data_target.fetch_moa_targets_for_ids([chembl_id], filter_target=target_chembl_id)
        moa_short = chembl_data_target.get_moa_short(moa_targets)
        indications = chembl_data_target.get_indications_for_drug(chembl_id)
        if not indications:
            # Still output row for drug with NA indication
            results.append({
                "Target Symbol": target_input,
                "Drug Name": drug_name,
                "MoA": moa_short,
                "Indication": "NA",
                "Approval Status": "NA",
                "Modality": modality,
                "nct_id": "",
                "phase": "",
                "overall_status": "",
                "sponsor": "",
                "source_class": "",
                "official_title": "",
                "intervention_types": ""
            })
        else:
            for ind in indications:
                approval = chembl_data_target.get_approval_status_from_indication(ind)
                # Fetch all trials for this drug-indication pair
                trials = db_client.fetch_trials_for_drug_and_indication(drug_name, ind.get("indication_name", ""))
                all_trials = []
                seen_nct_ids = set()

                if trials:
                    for trial in trials:
                        nct_id = trial.get("nct_id")
                        if nct_id and nct_id not in seen_nct_ids:
                            all_trials.append(trial)
                            seen_nct_ids.add(nct_id)
                else:
                    # Try all synonyms if no trials found with preferred name
                    drug_synonyms = chembl_data_target.get_drug_synonyms(chembl_id)
                    for drug_syn in drug_synonyms:
                        if drug_syn.lower() == (drug_name or "").lower():
                            continue  # already tried preferred name
                        syn_trials = db_client.fetch_trials_for_drug_and_indication(drug_syn, ind.get("indication_name", ""))
                        if syn_trials:
                            for trial in syn_trials:
                                nct_id = trial.get("nct_id")
                                if nct_id and nct_id not in seen_nct_ids:
                                    all_trials.append(trial)
                                    seen_nct_ids.add(nct_id)

                if not all_trials:
                    # If no trial for any synonym, still output the row
                    results.append({
                        "Target Symbol": target_input,
                        "Drug Name": drug_name,
                        "MoA": moa_short,
                        "Indication": ind.get("indication_name", "NA"),
                        "Approval Status": approval,
                        "Modality": modality,
                        "nct_id": "",
                        "phase": "",
                        "overall_status": "",
                        "sponsor": "",
                        "source_class": "",
                        "official_title": "",
                        "intervention_types": ""
                    })
                else:
                    for trial in all_trials:
                        results.append({
                            "Target Symbol": target_input,
                            "Drug Name": drug_name,
                            "MoA": moa_short,
                            "Indication": ind.get("indication_name", "NA"),
                            "Approval Status": approval,
                            "Modality": modality,
                            "nct_id": trial.get("nct_id", ""),
                            "phase": trial.get("phase", ""),
                            "overall_status": trial.get("overall_status", ""),
                            "sponsor": trial.get("sponsor", ""),
                            "source_class": trial.get("source_class", ""),
                            "official_title": trial.get("official_title", ""),
                            "intervention_types": trial.get("intervention_types", "")
                        })

    df = pd.DataFrame(results)
    df.to_csv(args.output, index=False)
    logging.info(f"Saved {len(df)} rows to {args.output}")

if __name__ == "__main__":
    main()