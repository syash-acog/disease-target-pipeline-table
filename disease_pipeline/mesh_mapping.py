import requests
import xml.etree.ElementTree as ET
import time
from fastapi import HTTPException
import os


MAX_RESULTS = 10000
NCBI_API_KEY = os.getenv('NCBI_API_KEY')
RATE_LIMIT_RETRY_PERIOD = 300
EMAIL = os.getenv('NCBI_EMAIL')
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def get_mesh_term_for_disease(disease_name):
    """
    Fetch the MeSH term for a given disease name from the NCBI MeSH database.
    
    Args:
        disease_name (str): The disease name to search for.
        
    Returns:
        str: The MeSH term for the disease, or None if not found.
    """
    params = {
        "db": "mesh",           
        "term": disease_name,   
        "retmode": "xml",
        "api_key": NCBI_API_KEY      
    }

    try:
        # Send the request to the API
        response = requests.get(BASE_URL + "esearch.fcgi", params=params)
        time.sleep(1)
        if response.status_code == 429:
            # raise Exception("Too Many Requests: You are being rate-limited. Please try again later.")
            rate_limited_until = time.time() + RATE_LIMIT_RETRY_PERIOD
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again after {RATE_LIMIT_RETRY_PERIOD} seconds.")

        response.raise_for_status()

        # Parse the XML response
        root = ET.fromstring(response.content)
        
        # Find the <TermSet> with <Field> == 'MeSH Terms'
        for term_set in root.findall(".//TermSet"):
            field = term_set.find("Field")
            term = term_set.find("Term")
            if field is not None and term is not None and field.text == "MeSH Terms":
                # Clean the MeSH term (remove quotes and brackets)
                return term.text.replace('"', '').replace("[MeSH Terms]", "").strip()

        return None
    
    except HTTPException as e:
        raise e

    except requests.RequestException as e:
        print(f"An error occurred while fetching the MeSH term: {e}")
        return None
    
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None