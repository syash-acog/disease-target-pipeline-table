from llm_client import LLMClient
from db_client import DBClient
from extractor import DrugExtractor
import pandas as pd
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def main():
    logging.info("Initializing LLM client...")
    llm_client = LLMClient()
    
    logging.info("Initializing database client...")
    db_client = DBClient()
    
    logging.info("Fetching data from the database...")
    data = db_client.fetch_data()
    logging.info(f"Fetched {len(data)} rows from the database.")

    # Limit the data for testing purposes
    data = data[:10]
    logging.info(f"Processing only the first {len(data)} rows for testing.")
    
    logging.info("Initializing drug extractor...")
    drug_extractor = DrugExtractor(llm_client)
    
    logging.info("Extracting drug names using LLM...")
    extracted_drugs = drug_extractor.extract_drug_names(data)
    logging.info(f"Extraction complete. Processed {len(extracted_drugs)} rows.")

    nctid_to_extracted = {
        row["nct_id"]: ", ".join(row["extracted_drugs"]) if isinstance(row["extracted_drugs"], list) else row["extracted_drugs"]
        for row in extracted_drugs
    }
    for row in data:
        row["extracted_drugs"] = nctid_to_extracted.get(row["nct_id"], "")

    logging.info("Saving extracted drug names to Parquet file...")
    df = pd.DataFrame(data)
    df.to_parquet('extracted_drugs.parquet', index=False)
    df.to_csv('extracted_drugs.csv', index=False)
    logging.info("Saved extracted drug names to extracted_drugs.parquet.")

if __name__ == "__main__":
    main()