import requests
import json

def get_all_chembl_ids(drug_name):
    """
    Returns a set of all matching ChEMBL IDs for a given drug_name,
    covering preferred name, synonyms, and partial matches.
    """
    base = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
    params_list = [
        {"pref_name__iexact": drug_name},
        {"molecule_synonyms__synonym__iexact": drug_name},
        {"pref_name__icontains": drug_name},
        {"molecule_synonyms__synonym__icontains": drug_name},
        {"molecule_synonyms__molecule_synonym__iexact": drug_name},
        {"molecule_synonyms__molecule_synonym__icontains": drug_name},
    ]
    ids = set()
    for params in params_list:
        # fetch up to 1000 entries per query
        params.update({"limit": 1000, "offset": 0})
        resp = requests.get(base, params=params)
        if resp.status_code == 200:
            for mol in resp.json().get("molecules", []):
                ids.add(mol["molecule_chembl_id"])
        else:
            print(f"[ERROR] ChEMBL search failed ({resp.status_code}) for params {params}")
    return ids

def fetch_target_name(target_chembl_id):
    """
    Fetches the preferred name of a target given its ChEMBL target ID.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("pref_name", "NA")
    else:
        print(f"[WARN] Failed to fetch target name ({resp.status_code}) for {target_chembl_id}")
        return "NA"

def fetch_moa_targets_for_ids(chembl_ids):
    """
    Returns a list of tuples (chembl_id, mechanism_of_action, target_name)
    aggregated across all provided ChEMBL IDs.
    """
    mechanisms = []
    for chembl_id in chembl_ids:
        mech_url = (
            "https://www.ebi.ac.uk/chembl/api/data/mechanism.json"
            f"?molecule_chembl_id={chembl_id}&limit=1000&offset=0"
        )
        resp = requests.get(mech_url)
        if resp.status_code == 200:
            for mech in resp.json().get("mechanisms", []):
                moa = mech.get("mechanism_of_action") or "NA"
                tgt_id = mech.get("target_chembl_id")
                tgt_name = fetch_target_name(tgt_id) if tgt_id else "NA"
                mechanisms.append((chembl_id, moa, tgt_name))
        else:
            print(f"[WARN] Mechanism fetch failed ({resp.status_code}) for {chembl_id}")
    return mechanisms

def fetch_moa_and_targets_via_chembl(drug_name):
    """
    Main entry: given a drug_name string, retrieves all MoA and target info
    from ChEMBL for all matched molecule IDs.
    """
    chembl_ids = get_all_chembl_ids(drug_name)
    if not chembl_ids:
        print(f"[WARN] No ChEMBL IDs found for '{drug_name}'.")
        return []
    results = fetch_moa_targets_for_ids(chembl_ids)
    if not results:
        print(f"[WARN] No mechanism/target data found in ChEMBL for '{drug_name}'.")
    return results

def fetch_and_write_chembl_summary(drug_name, output_json="summary.json"):
    """
    Fetch all MoA/target info from ChEMBL and write to a JSON summary file.
    """
    data = []
    for chembl_id, moa, tgt in fetch_moa_and_targets_via_chembl(drug_name):
        data.append({
            "chembl_id": chembl_id,
            "mechanism_of_action": moa,
            "target_name": tgt
        })
    if not data:
        print(f"[ERROR] No data to write for '{drug_name}'.")
        return
    with open(output_json, "w") as f:
        json.dump({"drug_name": drug_name, "mechanisms": data}, f, indent=2)
    print(f"[INFO] Summary saved to {output_json}")

def fetch_moa_and_target(drug_name):
    """
    Returns the first (moa, target) found for a drug name, using all ChEMBL IDs.
    """
    results = fetch_moa_and_targets_via_chembl(drug_name)
    for _, moa, target in results:
        if moa != "NA" and target != "NA":
            return moa, target
    # If none found, but there are results, return the first (may be NA)
    if results:
        _, moa, target = results[0]
        return moa, target
    print(f"[WARN] No MoA/target found in ChEMBL for '{drug_name}'.")
    return "NA", "NA"

if __name__ == "__main__":
    drug_name = input("Enter drug name: ").strip()
    filename = f"{drug_name.lower().replace(' ', '_')}_chembl_summary.json"
    fetch_and_write_chembl_summary(drug_name, filename)
