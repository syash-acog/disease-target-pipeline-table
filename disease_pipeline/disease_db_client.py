import os
import psycopg2
from dotenv import load_dotenv
from mesh_mapping import get_mesh_term_for_disease
import logging

load_dotenv()

class DBClient:
    def __init__(self):
        self.host = os.getenv("db_host")
        self.port = os.getenv("db_port")
        self.userid = os.getenv("db_userid")
        self.pwd = os.getenv("db_password")
        self.connection = self.connect_to_db()

    def connect_to_db(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.userid,
            password=self.pwd,
            dbname="aact_db"  # Updated to correct DB name
        )

    def fetch_data(self, disease_name):
        """
        Fetches clinical trial data for both the original disease name (name 1)
        and its MeSH term (name 2), merging results automatically for any disease.
        """
        mesh_term = get_mesh_term_for_disease(disease_name)
        if not mesh_term:
            mesh_term = ""
        logging.info(f"Found MeSH term: {mesh_term}")

        query = """
        WITH all_trials AS (
            -- Trials matching the original disease name (name 1)
            SELECT
                s.nct_id,
                c.downcase_name AS condition_name,
                s.phase,
                s.overall_status,
                s.source AS sponsor,
                s.source_class,
                s.official_title,
                STRING_AGG(i.name, ', ') AS drug_names,
                STRING_AGG(i.intervention_type, ', ') AS intervention_types
            FROM
                ctgov.conditions c
            JOIN
                ctgov.studies s ON c.nct_id = s.nct_id
            JOIN
                ctgov.interventions i ON s.nct_id = i.nct_id
            WHERE
                c.downcase_name = %s
                AND s.study_type = 'INTERVENTIONAL'
                AND i.intervention_type IN ('DRUG', 'BIOLOGICAL')
            GROUP BY
                s.nct_id, c.downcase_name, s.phase, s.overall_status, s.source, s.source_class, s.official_title

            UNION

            -- Trials matching the MeSH term (name 2)
            SELECT
                s.nct_id,
                bc.downcase_mesh_term AS condition_name,
                s.phase,
                s.overall_status,
                s.source AS sponsor,
                s.source_class,
                s.official_title,
                STRING_AGG(i.name, ', ') AS drug_names,
                STRING_AGG(i.intervention_type, ', ') AS intervention_types
            FROM
                ctgov.browse_conditions bc
            JOIN
                ctgov.studies s ON bc.nct_id = s.nct_id
            JOIN
                ctgov.interventions i ON s.nct_id = i.nct_id
            WHERE
                bc.downcase_mesh_term = %s
                AND s.study_type = 'INTERVENTIONAL'
                AND i.intervention_type IN ('DRUG', 'BIOLOGICAL')
            GROUP BY
                s.nct_id, bc.downcase_mesh_term, s.phase, s.overall_status, s.source, s.source_class, s.official_title
        )
        SELECT DISTINCT * FROM all_trials;
        """

        with self.connection.cursor() as cur:
            cur.execute(query, (disease_name.lower(), mesh_term.lower()))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
        return data