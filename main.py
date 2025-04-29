from llm_client import LLMClient
from db_client import DBClient
from extractor import DrugExtractor
import chembl_data
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    disease_name = input("Enter disease name: ").strip().lower()
    logging.info(f"User provided disease: {disease_name}")

    logging.info("Initializing LLM client...")
    llm_client = LLMClient()
    
    logging.info("Initializing database client...")
    db_client = DBClient()
    
    logging.info("Fetching data from the database...")
    data = db_client.fetch_data(disease_name)
    logging.info(f"Fetched {len(data)} rows from the database.")

    # Limit the data for testing purposes
    data = data[:30]
    logging.info(f"Processing only the first {len(data)} rows for testing.")
    
    logging.info("Initializing drug extractor...")
    drug_extractor = DrugExtractor(llm_client)
    
    logging.info("Extracting drug names using LLM...")
    extracted_drugs = drug_extractor.extract_drug_names(data)
    logging.info(f"Extraction complete. Processed {len(extracted_drugs)} rows.")
        # Save LLM-processed drug extraction to a separate file
    logging.info("Saving LLM-processed drug extraction to CSV file...")
    df_llm = pd.DataFrame(extracted_drugs)
    df_llm.to_csv('llm_extracted_drugs.csv', index=False)
    logging.info("Saved LLM-processed drug extraction to llm_extracted_drugs.csv.")

    nctid_to_extracted = {
        row["nct_id"]: ", ".join(row["extracted_drugs"]) if isinstance(row["extracted_drugs"], list) else row["extracted_drugs"]
        for row in extracted_drugs
    }
    nctid_to_moa = {}
    nctid_to_target = {}

    for row in extracted_drugs:
        drug_list = row["extracted_drugs"]
        if isinstance(drug_list, str):
            drug_list = [d.strip() for d in drug_list.split(",") if d.strip()]
        moa_list = []
        target_list = []
        for drug in drug_list:
            moa, target = chembl_data.fetch_moa_and_target(drug)
            moa_list.append(moa if moa else "NA")
            target_list.append(target if target else "NA")
        nctid_to_moa[row["nct_id"]] = "; ".join(moa_list) if moa_list else ""
        nctid_to_target[row["nct_id"]] = "; ".join(target_list) if target_list else ""

    for row in data:
        extracted = nctid_to_extracted.get(row["nct_id"], "")
        if isinstance(extracted, list):
            row["extracted_drugs"] = ", ".join(extracted)
        else:
            row["extracted_drugs"] = extracted
        row["moa"] = nctid_to_moa.get(row["nct_id"], "")
        row["target"] = nctid_to_target.get(row["nct_id"], "")

    logging.info("Saving extracted drug names and MoA/target to CSV file...")
    df = pd.DataFrame(data)
    df.to_csv('extracted_drugs_with_moa_target.csv', index=False)
    logging.info("Saved extracted drug names to extracted_drugs_with_moa_target.csv.")

if __name__ == "__main__":
    main()