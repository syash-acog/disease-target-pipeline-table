import requests
import json

def get_chembl_id_from_name(drug_name):
    # Try preferred name first
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule.json?pref_name__iexact={drug_name}"
    print(f"[INFO] Searching ChEMBL for drug name: {drug_name}")
    resp = requests.get(url)
    if resp.status_code == 200:
        results = resp.json().get("molecules", [])
        if results:
            chembl_id = results[0]["molecule_chembl_id"]
            print(f"[INFO] Found ChEMBL ID by preferred name: {chembl_id}")
            return chembl_id
    else:
        print(f"[ERROR] Failed to search ChEMBL (status {resp.status_code})")
        return None

    # Try synonyms if not found by preferred name
    print(f"[INFO] Trying synonyms for drug name: {drug_name}")
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule.json?molecule_synonyms__molecule_synonym__iexact={drug_name}"
    resp = requests.get(url)
    if resp.status_code == 200:
        results = resp.json().get("molecules", [])
        if results:
            chembl_id = results[0]["molecule_chembl_id"]
            print(f"[INFO] Found ChEMBL ID by synonym: {chembl_id}")
            return chembl_id
        else:
            print(f"[WARN] No ChEMBL ID found for drug name or synonym: {drug_name}")
            return None
    else:
        print(f"[ERROR] Failed to search ChEMBL synonyms (status {resp.status_code})")
        return None

def fetch_target_name(target_chembl_id):
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("pref_name", None)
    else:
        return None

def fetch_and_write_summary(drug_name, output_json="summary.json"):
    chembl_id = get_chembl_id_from_name(drug_name)
    if not chembl_id:
        print("[ERROR] Cannot fetch data without ChEMBL ID.")
        return

    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    endpoints = {
        "molecule": f"{base_url}/molecule/{chembl_id}.json",
        "indications": f"{base_url}/drug_indication.json?drug_chembl_id={chembl_id}",
        "mechanisms": f"{base_url}/mechanism.json?molecule_chembl_id={chembl_id}"
    }
    data = {}
    for key, url in endpoints.items():
        print(f"[INFO] Fetching {key} from {url}")
        resp = requests.get(url)
        if resp.status_code == 200:
            data[key] = resp.json()
        else:
            print(f"[WARN] Failed to fetch {key} (status {resp.status_code})")
            data[key] = {}

    # Mechanism of action and target (always include all)
    mechanisms = data.get("mechanisms", {}).get("mechanisms", [])
    moa_list = []
    for mech in mechanisms:
        moa = mech.get("mechanism_of_action")
        target_chembl_id = mech.get("target_chembl_id")
        target_name = fetch_target_name(target_chembl_id) if target_chembl_id else None
        moa_list.append({
            "mechanism_of_action": moa,
            "target_name": target_name
        })

    # Indications: include all
    indications = data.get("indications", {}).get("drug_indications", [])
    indication_names = []
    for ind in indications:
        name = ind.get("efo_term") or ind.get("mesh_heading")
        if name:
            indication_names.append(name)

    summary = {
        "mechanisms": moa_list,
        "indications": indication_names
    }

    with open(output_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[INFO] Summary saved to {output_json}")

if __name__ == "__main__":
    drug_name = input("Enter drug name: ").strip()
    base_filename = drug_name.lower().replace(" ", "_")
    summary_json = f"{base_filename}_summary.json"
    fetch_and_write_summary(drug_name, summary_json)
