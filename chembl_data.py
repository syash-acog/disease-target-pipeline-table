import requests
import json
import csv

def get_chembl_id_exact(drug_name):
    """
    Attempts to find the best ChEMBL ID for a drug name.
    First tries exact matches (preferred name and synonyms).
    If no exact match is found, tries partial matches.
    Returns a list with the first matching ChEMBL ID, or an empty list if not found.
    """
    base = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
    # 1. Try exact matches
    params_list = [
        {"pref_name__iexact": drug_name},
        {"molecule_synonyms__synonym__iexact": drug_name},
        {"molecule_synonyms__molecule_synonym__iexact": drug_name},
    ]
    for params in params_list:
        params.update({"limit": 200, "offset": 0})
        resp = requests.get(base, params=params)
        if resp.status_code == 200:
            molecules = resp.json().get("molecules", [])
            if molecules:
                chembl_id = molecules[0]["molecule_chembl_id"]
                return [chembl_id]
    # 2. If no exact match, try partial matches
    params_list_partial = [
        {"pref_name__icontains": drug_name},
        {"molecule_synonyms__synonym__icontains": drug_name},
        {"molecule_synonyms__molecule_synonym__icontains": drug_name},
    ]
    for params in params_list_partial:
        params.update({"limit": 200, "offset": 0})
        resp = requests.get(base, params=params)
        if resp.status_code == 200:
            molecules = resp.json().get("molecules", [])
            if molecules:
                chembl_id = molecules[0]["molecule_chembl_id"]
                return [chembl_id]
    return []

def fetch_molecule_type(chembl_id):
    """
    Given a ChEMBL ID, fetches the molecule type (e.g., 'Small molecule', 'Protein').
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("molecule_type", "NA")
    else:
        print(f"[WARN] Failed to fetch molecule type ({resp.status_code}) for {chembl_id}")
        return "NA"

def fetch_approval_status(chembl_id, disease_name):
    """
    Checks if a drug (by ChEMBL ID) is approved for a given disease/indication.
    Returns 'Approved' if max_phase_for_ind is 4 for the indication,
    'Not Approved' if found but not phase 4, or 'NA' if not found.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/drug_indication.json?molecule_chembl_id={chembl_id}&limit=1000"
    resp = requests.get(url)
    if resp.status_code == 200:
        for ind in resp.json().get("drug_indications", []):
            # Try to match disease_name to efo_term or mesh_heading (case-insensitive, trimmed)
            efo_term = ind.get("efo_term", "").strip().lower()
            mesh_heading = ind.get("mesh_heading", "").strip().lower()
            if disease_name and (
                disease_name.strip().lower() == efo_term or
                disease_name.strip().lower() == mesh_heading or
                disease_name.strip().lower() in efo_term or
                disease_name.strip().lower() in mesh_heading
            ):
                if float(ind.get("max_phase_for_ind", 0)) == 4:
                    return "Approved"
                else:
                    return "Not Approved"
    return "NA"

def fetch_moa_targets_for_ids(chembl_ids):
    """
    For a list of ChEMBL IDs, fetches mechanism of action (MoA) and target information.
    Returns a list of tuples: (chembl_id, mechanism_of_action, target_name).
    If no mechanism is found, tries to get the first target_chembl_id from the activity endpoint as a fallback.
    """
    mechanisms = []
    for chembl_id in chembl_ids:
        mech_url = (
            "https://www.ebi.ac.uk/chembl/api/data/mechanism.json"
            f"?molecule_chembl_id={chembl_id}&limit=1000&offset=0"
        )
        resp = requests.get(mech_url)
        found_mechanism = False
        if resp.status_code == 200:
            for mech in resp.json().get("mechanisms", []):
                moa = mech.get("mechanism_of_action") or "NA"
                tgt_id = mech.get("target_chembl_id")
                tgt_name = fetch_target_name(tgt_id) if tgt_id else "NA"
                mechanisms.append((chembl_id, moa, tgt_name))
                found_mechanism = True
        else:
            print(f"[WARN] Mechanism fetch failed ({resp.status_code}) for {chembl_id}")

        # Fallback: If no mechanism found, try activity endpoint for target_chembl_id
        if not found_mechanism:
            act_url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json?molecule_chembl_id={chembl_id}&limit=1"
            act_resp = requests.get(act_url)
            if act_resp.status_code == 200:
                activities = act_resp.json().get("activities", [])
                if activities:
                    tgt_id = activities[0].get("target_chembl_id")
                    tgt_name = fetch_target_name(tgt_id) if tgt_id else "NA"
                    mechanisms.append((chembl_id, "NA", tgt_name))
    return mechanisms

def fetch_target_name(target_chembl_id):
    """
    Given a ChEMBL target ID, fetches the gene symbol (GENE_SYMBOL) for the target.
    Falls back to the preferred name if no gene symbol is found.
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        target = resp.json()
        # Search for GENE_SYMBOL in target_components
        for comp in target.get("target_components", []):
            for syn in comp.get("target_component_synonyms", []):
                if syn.get("syn_type") == "GENE_SYMBOL":
                    return syn.get("component_synonym", "NA")
        # Fallback to pref_name
        return target.get("pref_name", "NA")
    else:
        print(f"[WARN] Failed to fetch target name ({resp.status_code}) for {target_chembl_id}")
        return "NA"

def extract_moa_keyword(moa):
    """
    Extracts a short keyword from the MoA string (e.g., 'inhibitor', 'agonist').
    If a known keyword is found, returns it; otherwise, returns the last word or 'NA'.
    """
    for kw in ["inhibitor", "agonist", "antagonist", "modulator", "blocker", "activator"]:
        if kw in moa.lower():
            return kw
    # fallback: last word
    return moa.split()[-1] if moa else "NA"

def get_moa_short(moa_targets):
    """
    For a list of (chembl_id, moa, target) tuples, returns a short MoA string.
    Format: 'GENE_SYMBOL: keyword' for each pair, comma-separated for multiple pairs.
    Returns 'NA' if no valid pairs are found.
    """
    short_blocks = []
    for chembl_id, moa, target in moa_targets:
        if target and target != "NA":
            moa_kw = extract_moa_keyword(moa)
            short_blocks.append(f"{target}: {moa_kw}")
    return ", ".join(short_blocks) if short_blocks else "NA"

def format_multi_drug_output(blocks):
    """
    Formats output for multiple drugs and multiple values per drug.
    - Multiple values for a single drug are comma-separated.
    - Multiple drugs in a row are pipe-separated.
    Example: [["A", "B"], ["C"]] -> "A, B | C"
    """
    return " | ".join([", ".join([v for v in vals if v and v != "NA"]) if vals else "NA" for vals in blocks])

def fetch_and_write_chembl_summary_csv(drug_names, output_csv="summary.csv", disease_name=None):
    """
    Writes a summary CSV for a list of drug names.
    Each row includes ChEMBL IDs, MoA (with fallback), target, modality, approval status, and short MoA symbol.
    If MoA is empty but target is present, MoA column is filled with 'TARGET: keyword'.
    """
    fieldnames = [
        "input_drug", "chembl_ids", "mechanism_of_action", "target_name",
        "modality", "approval_status", "moa_short"
    ]
    data = []
    for drug_name in drug_names:
        chembl_ids = get_chembl_id_exact(drug_name)
        # Fetch MoA and target
        moa_targets = fetch_moa_targets_for_ids(chembl_ids)
        moa_str = get_moa_with_target_fallback(moa_targets)
        target_list = [mt[2] for mt in moa_targets if mt[2] and mt[2] != "NA"]
        target_str = "; ".join(target_list) if target_list else "NA"
        # Get the original full modality column as before
        moltype_str = "; ".join([fetch_molecule_type(cid) for cid in chembl_ids if cid]) if chembl_ids else "NA"
        # Approval status (use first chembl_id if available)
        if chembl_ids and disease_name:
            approval_status = fetch_approval_status(chembl_ids[0], disease_name)
        else:
            approval_status = "NA"
        # Short MoA symbol: TARGET_SYMBOL: keyword
        moa_short_blocks = []
        for chembl_id, moa, target in moa_targets:
            if target and target != "NA":
                moa_kw = extract_moa_keyword(moa)
                moa_short_blocks.append(f"{target}: {moa_kw}")
        moa_short = "; ".join(moa_short_blocks) if moa_short_blocks else "NA"
        data.append({
            "input_drug": drug_name,
            "chembl_ids": ", ".join(chembl_ids) if chembl_ids else "NA",
            "mechanism_of_action": moa_str,
            "target_name": target_str,
            "modality": moltype_str,
            "approval_status": approval_status,
            "moa_short": moa_short
        })
    if not data:
        print(f"[ERROR] No data to write for input drugs: {drug_names}")
        return
    with open(output_csv, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"[INFO] Summary saved to {output_csv}")

# # The following function is not used in the main workflow but kept for reference.
# def get_moa_with_target_fallback(moa_targets):
#     """
#     Returns a string for the MoA column.
#     If MoA is empty but target is present, returns 'TARGET: keyword' for each target.
#     """
#     moa_list = [mt[1] for mt in moa_targets if mt[1] and mt[1] != "NA"]
#     target_list = [mt[2] for mt in moa_targets if mt[2] and mt[2] != "NA"]
#     if moa_list:
#         return "; ".join(moa_list)
#     elif target_list:
#         # Use empty string for keyword fallback, or customize as needed
#         return "; ".join(f"{target}: {extract_moa_keyword('')}" for target in target_list)
#     else:
#         return "NA"

if __name__ == "__main__":
    drug_input = input("Enter drug names (comma separated): ").strip()
    drug_names = [d.strip() for d in drug_input.split(",") if d.strip()]
    disease_name = input("Enter disease name (optional): ").strip() or None
    filename = "chembl_summary.csv"
    fetch_and_write_chembl_summary_csv(drug_names, filename, disease_name)
