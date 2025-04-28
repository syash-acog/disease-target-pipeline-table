import logging

class DrugExtractor:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def extract_drug_names(self, intervention_data):
        prompt_template = (
        '''Act like a clinical trials expert, given a set of interventions, list down only the drug's name used. Also, include multiple drugs if it has been used in any case. Ignore any other information like dosage or placebo, etc. 
            Example 1:
            VC005 low dose group, VC005 high dose group, VC005 Placebo group

            output:
            VC005

            Example 2:
            CGB-500 with 0.5% tofacitinib, CGB-500 Ointment with 1% tofacitinib, Vehicle (placebo)

            output:
            CGB-500, tofacitinib

            Example 3:
            Dual Integrin Antagonist

            output:
            Dual Integrin Antagonist

            Example 4:
            Placebo, Levalbuterol tartrate MDI, racemic albuterol MDI

            output:
            Levalbuterol tartrate MDI, racemic albuterol MDI

            Example 5:
            injected insulin, inhaled insulin, Insulin aspart, Human Insulin Inhalation Powder"

            output:
            insulin aspart

        **To Note:**
            1. Extract and only exact Core drug name should be included in the output.
            2. No other uncessary information should be included in the output.
            3. The drug names should be separated by commas.
            4. Dont include placebo
            5. If a drug name includes an administration route or form, exclude it and only return the core drug name(s). (e.g., "inhaled insulin", "injected insulin", "spary", "oral","nasal" etc.)


        '''
        )
        results = []
        for idx, row in enumerate(intervention_data):
            drug_names_str = row['drug_names']
            prompt = prompt_template + "\n" + drug_names_str
            logging.info(f"Processing row {idx+1}/{len(intervention_data)} (nct_id={row['nct_id']}) with LLM...")
            response = self.llm_client.extract_drugs(prompt)
            drugs = self.process_response(response)
            results.append({
                "nct_id": row["nct_id"],
                "original_drug_names": drug_names_str,
                "extracted_drugs": drugs
            })
        return results

    def process_response(self, response):
        drug_names = [name.strip() for name in response.split(',')]
        return drug_names