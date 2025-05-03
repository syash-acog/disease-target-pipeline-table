import requests

def get_target_chembl_id(target_input):
    """
    Given a gene symbol or ChEMBL target ID, returns the ChEMBL target ID.
    """
    if target_input.upper().startswith("CHEMBL"):
        return target_input
    url = f"https://www.ebi.ac.uk/chembl/api/data/target.json?target_components__target_component_synonyms__component_synonym__iexact={target_input}&limit=1"
    resp = requests.get(url)
    if resp.status_code == 200:
        targets = resp.json().get("targets", [])
        if targets:
            return targets[0]["target_chembl_id"]
    return None

def get_drugs_for_target(target_chembl_id):
    """
    Returns a list of drugs (dicts) that act on the given target (from ChEMBL).
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/mechanism.json?target_chembl_id={target_chembl_id}&limit=1000"
    resp = requests.get(url)
    drugs = []
    if resp.status_code == 200:
        seen = set()
        for mech in resp.json().get("mechanisms", []):
            mol = mech.get("molecule_chembl_id")
            if mol and mol not in seen:
                seen.add(mol)
                # Optionally fetch pref_name
                mol_url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{mol}.json"
                mol_resp = requests.get(mol_url)
                pref_name = mol_resp.json().get("pref_name") if mol_resp.status_code == 200 else None
                drugs.append({"molecule_chembl_id": mol, "pref_name": pref_name})
    return drugs

def fetch_molecule_type(chembl_id):
    """
    Given a ChEMBL ID, fetches the molecule type (e.g., 'Small molecule', 'Protein').
    Returns 'NA' if not found or on error.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/{chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("molecule_type", "NA")
    return "NA"

def fetch_moa_targets_for_ids(chembl_ids, filter_target=None):
    """
    For a list of ChEMBL IDs, fetches mechanism of action (MoA) and target information.
    If filter_target is set, only returns mechanisms for that target.
    Returns a list of tuples: (chembl_id, mechanism_of_action, target_symbol).
    """
    mechanisms = []
    for chembl_id in chembl_ids:
        url = f"https://www.ebi.ac.uk/chembl/api/data/mechanism.json?molecule_chembl_id={chembl_id}&limit=1000"
        resp = requests.get(url)
        if resp.status_code == 200:
            for mech in resp.json().get("mechanisms", []):
                tgt_id = mech.get("target_chembl_id")
                if filter_target and tgt_id != filter_target:
                    continue
                moa = mech.get("mechanism_of_action") or "NA"
                tgt_symbol = fetch_target_symbol(tgt_id) if tgt_id else "NA"
                mechanisms.append((chembl_id, moa, tgt_symbol))
    return mechanisms

def fetch_target_symbol(target_chembl_id):
    """
    Given a ChEMBL target ID, fetches the gene symbol (GENE_SYMBOL) for the target.
    Falls back to the preferred name if no gene symbol is found.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/target/{target_chembl_id}.json"
    resp = requests.get(url)
    if resp.status_code == 200:
        target = resp.json()
        for comp in target.get("target_components", []):
            for syn in comp.get("target_component_synonyms", []):
                if syn.get("syn_type") == "GENE_SYMBOL":
                    return syn.get("component_synonym", "NA")
        return target.get("pref_name", "NA")
    return "NA"

def extract_moa_keyword(moa):
    """
    Extracts a keyword from the MoA string (e.g., 'inhibitor', 'agonist').
    """
    for kw in ["inhibitor", "agonist", "antagonist", "modulator", "blocker", "activator"]:
        if kw in moa.lower():
            return kw
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

def get_indications_for_drug(chembl_id):
    """
    Returns a list of indication dicts for a given drug ChEMBL ID.
    Each dict contains at least 'indication_name' and 'max_phase_for_ind'.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/drug_indication.json?molecule_chembl_id={chembl_id}&limit=1000"
    resp = requests.get(url)
    indications = []
    if resp.status_code == 200:
        for ind in resp.json().get("drug_indications", []):
            # Use efo_term or mesh_heading as indication name
            name = (ind.get("efo_term") or ind.get("mesh_heading") or "NA")
            indications.append({
                "indication_name": name,
                "max_phase_for_ind": ind.get("max_phase_for_ind", "NA")
            })
    return indications

def get_approval_status_from_indication(ind):
    """
    Returns 'Approved' if max_phase_for_ind is 4, else 'Not Approved' or 'NA'.
    """
    try:
        if float(ind.get("max_phase_for_ind", 0)) == 4:
            return "Approved"
        else:
            return "Not Approved"
    except Exception:
        return "NA"