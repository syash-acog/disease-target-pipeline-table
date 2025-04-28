from chembl_webresource_client.new_client import new_client

def get_approval_year(drug_name: str) -> str:
    # 1. Lookup the molecule by name
    results = (
        new_client.molecule
                  .filter(pref_name__iexact=drug_name)
                  .only(['molecule_chembl_id', 'parent_chembl_id'])
    )
    if not results:
        raise ValueError(f"No molecule found for '{drug_name}'")

    # 2. Use parent_chembl_id (if present) otherwise molecule_chembl_id
    chembl_id = results[0].get('parent_chembl_id') or results[0]['molecule_chembl_id']

    # 3. Fetch the full molecule record
    molecule = new_client.molecule.get(chembl_id)

    # 4. Extract the first_approval year
    #    This is returned as a string (e.g. "2001") or None if unknown.
    return molecule.get('first_approval') or "Unknown"

# Example
if __name__ == "__main__":
    drug = "Imatinib"
    year = get_approval_year(drug)
    print(f"{drug} first approval year: {year}")
