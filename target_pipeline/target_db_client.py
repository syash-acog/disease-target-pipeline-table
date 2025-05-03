import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class TargetDBClient:
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
            dbname="aact_db"
        )

    def fetch_trials_for_drug_and_indication(self, drug_name, indication_name):
        """
        Fetches all clinical trial rows for a given drug and indication.
        Returns a list of dicts with all relevant columns.
        """
        query = f"""
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
            AND LOWER(i.name) LIKE %s
        GROUP BY
            s.nct_id, c.downcase_name, s.phase, s.overall_status, s.source, s.source_class, s.official_title;
        """
        with self.connection.cursor() as cur:
            cur.execute(query, (indication_name.lower(), f"%{drug_name.lower()}%"))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
        return data