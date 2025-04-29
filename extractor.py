import logging

class DrugExtractor:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def extract_drug_names(self, intervention_data):
        prompt_template = (
        '''
        You are a clinical-trials expert whose sole task is to extract CORE DRUG NAMES from a free-text list of interventions.

        Rules:
        1. Return **only** the exact, core drug name(s), separated by commas.
        2. Exclude all dosage, administration routes/forms (e.g., injected, inhaled, oral, topical, MDI, powder, patch, spray, infusion, intravenous, subcutaneous, intramuscular, nasal), formulation details, **stereochemical descriptors (e.g., 'racemic', 'levo', 'dex', 'D-'), and common salt or ester forms (e.g., 'tartrate', 'hydrochloride', 'acetate', 'fumarate', 'succinate', 'phosphate', 'sodium', 'potassium')**.
        3. Do **not** return “placebo” or vehicle controls.
        4. Do **not** extract generic drug-class terms (e.g. “corticosteroid(s)”, “NSAIDs”, “antibiotics”, "integrin antagonist")—only specific, named molecules. Exclude natural products, supplements, or herbal extracts.
        5. If a term is purely a route/formulation (e.g. “inhaled insulin”) or a non-drug formulation (e.g. “silver cream”), **do not** extract it.
        6. If **no** core drug name remains after filtering, output a completely empty string (no characters).
        7. If a single intervention description refers to a combination of multiple core drug names (e.g., linked by '/', '+', 'and', or listed together), extract *each* core drug name individually.

        Examples:

        Example 1
        input:
        VC005 low dose group, VC005 high dose group, VC005 Placebo group
        output:
        VC005

        Example 2
        input:
        CGB-500 with 0.5% tofacitinib, CGB-500 Ointment with 1% tofacitinib, Vehicle (placebo)
        output:
        CGB-500, tofacitinib

        Example 3
        input:
        Dual Integrin Antagonist
        output:
        

        Example 4
        input:
        Placebo, Levalbuterol tartrate MDI, racemic albuterol MDI
        output:
        Levalbuterol, albuterol

        Example 5
        input:
        injected insulin, inhaled insulin, Insulin aspart, Human Insulin Inhalation Powder
        output:
        insulin aspart

        Example 6
        input:
        injected insulin, inhaled insulin, topical corticosteroids, Human Insulin Inhalation Powder, corticosteroids, Borage oil, Ginkgo biloba
        output:
        

        Example 7
        input:
        Budesonide/Formoterol pMDI, Salbutamol rescue inhaler
        output:
        budesonide, formoterol, salbutamol

        Example 8
        input:
        DrugX + DrugY combination tablet
        output:
        DrugX, DrugY

        '''
        )

        all_results = []
        for idx, row in enumerate(intervention_data, 1):
            logging.info(f"Processing row {idx}/{len(intervention_data)}: nct_id {row['nct_id']}")
            prompt = prompt_template + f"\ninput:\n{row['drug_names']}\n\noutput:"
            response = self.llm_client.extract_drugs(prompt)
            drugs = [d.strip() for d in response.split(',') if d.strip()]
            all_results.append({
                "nct_id": row["nct_id"],
                "original_drug_names": row["drug_names"],
                "extracted_drugs": drugs
            })
        logging.info(f"All rows processed. Total extracted: {len(all_results)}")
        return all_results