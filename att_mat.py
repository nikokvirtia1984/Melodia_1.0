import pandas as pd
from typing import List, Dict, Any
import os
from database import Database
db = Database()

class MaterialAttributeTranslator:
    """
    A class to fetch and translate the compressed ATT_MAT string
    from a material record, loading lookup data from external CSV files.
    """

    # --- 0. STATIC LOOKUP DATA (Now file paths instead of content strings) ---
    _MATFORM_FILE = "matform_content.csv"
    _MATSTOR_FILE = "matstor_content.csv"
    _SAXEEBI_FILE = "saxeebi_content.csv"

    _SIMPLE_RULES: Dict[str, Dict[str, str]] = {
        'შენახვის პირობები': {'0': 'შენახვა ჩვეულებრივ ადგილზე', '1': 'შენახვა ბნელ ადგილზე'},
        'Aსია, Bსია': {'A': 'A-სია', 'B': 'B-სია'},
        'სპეც კონტროლი': {'0': 'არ ექვემდებარება სპეც კონტროლს', '1': 'სპეც კონტროლს ექვემდებარება',
                          '2': 'არ ექვემდებარება სპეც კონტროლს'},
        'დღგ': {'0': 'არ იბეგრება დღგ-თი', '1': 'იბეგრება დღგ-თი'},
        'შესყიდვის დღგ': {'0': 'შესყიდვის დღგ არ არის გადახდილი', '1': 'შესყიდვის დღგ გადახდილია'},
        'რეგისტრაცია': {'0': 'რეგისტრაცია არ უნდა', '1': 'რეგისტრაცია უნდა'},
        'რეცეპტით გაცემა': {'0': 'გაცემა ურეცეპტოდ', '1': 'გაცემა რეცეპტით'},
        'მედიკამენტი/არამედიკამენტი': {'0': 'მედიკამენტი', '1': 'არამედიკამენტი'},
        'ჯიხურში გაყიდვის უფლება': {'0': 'ჯიხურში გაყიდვა ნებადართულია', '1': 'ჯიხურში გაყიდვა აკრძალულია'},
    }

    # EXAMPLE_ATT_MAT_STRING = "0100200000111000"

    def __init__(self):
        """Initializes the translator and builds all lookup maps from CSV files."""

        # Build multi-character lookup maps from file content
        # print(f"Loading lookup data from: {self._MATFORM_FILE}, {self._MATSTOR_FILE}, {self._SAXEEBI_FILE}")
        self.MATFORM_MAP = self._create_lookup_map_from_file(
            self._MATFORM_FILE, 'cod_form', 'nam_form')
        self.MATSTOR_MAP = self._create_lookup_map_from_file(
            self._MATSTOR_FILE, 'cod_stor', 'nam_stor')
        self.SAXEEBI_MAP = self._create_lookup_map_from_file(
            self._SAXEEBI_FILE, 'cod_saxe', 'nam_saxe')

        # Combine all rules for unified lookup
        self.ALL_RULES: Dict[str, Dict[str, str]] = {
            'ფორმების კოდი': self.MATFORM_MAP,
            'მაცივარიში შენახვის პირობები': self.MATSTOR_MAP,
            'გამოშვების სახე': self.SAXEEBI_MAP,
            **self._SIMPLE_RULES
        }

    def _create_lookup_map_from_file(self, file_path: str, code_col: str, name_col: str) -> Dict[str, str]:
        """Private helper method to load a map from a local CSV file."""
        if not os.path.exists(file_path):
            print(f"FATAL ERROR: Lookup file not found: {file_path}")
            return {}

        try:
            # Read directly from the file path
            df = pd.read_csv(file_path)

            # Use 'errors=coerce' for robustness against bad data in the code column
            # Convert to integer then string for clean keys (e.g., 1.0 -> '1')
            df['code_str'] = pd.to_numeric(df[code_col], errors='coerce').fillna(0).astype(int).astype(str)

            return df.set_index('code_str')[name_col].to_dict()

        except Exception as e:
            print(f"FATAL ERROR: Failed to process lookup data from {file_path}. Details: {e}")
            return {}

    def get_material_attribute(self, material_name: str) -> str | None:
        """Fetches the raw ATT_MAT string from the database, or uses a fallback."""
        # if self.db is None:
        #     print("Warning: Database instance not provided. Using test string.")
        #     return self.EXAMPLE_ATT_MAT_STRING

        try:
            # --- ACTUAL DB QUERY LOGIC HERE ---
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT "ATT_MAT" FROM public.mater1 WHERE "NAM_MAT" = %s;
                    """, (material_name,))

                    result = cursor.fetchone()

                    if result and result[0]:
                        return result[0].strip()
                    else:
                        return None

        except Exception as e:
            print(f"Database error while fetching ATT_MAT ({e}). Using test string.")

    def translate_attributes(self, attribute_value_str: str) -> List[str]:
        """
        Parses the ATT_MAT string, translates the codes using the internal
        ALL_RULES map, and returns a list of descriptive strings (attmat).
        """
        if not attribute_value_str or len(attribute_value_str) < 16:
            return ["Error: ATT_MAT string is too short or empty for full parsing."]

        product_description = {
            'ფორმების კოდი': attribute_value_str[0:2].lstrip('0'),
            'მაცივარიში შენახვის პირობები': attribute_value_str[2],
            'შენახვის პირობები': attribute_value_str[3],
            'Aსია, Bსია': attribute_value_str[4],
            'სპეც კონტროლი': attribute_value_str[5],
            'დღგ': attribute_value_str[6],
            'შესყიდვის დღგ': attribute_value_str[7],
            'გამოშვების სახე': attribute_value_str[8:11].lstrip('0'),
            'რეგისტრაცია': attribute_value_str[11],
            'რეცეპტით გაცემა': attribute_value_str[12],
            'მედიკამენტი/არამედიკამენტი': attribute_value_str[13],
            'ჯიხურში გაყიდვის უფლება': attribute_value_str[14],
            'დანიშნულება': attribute_value_str[15]
        }

        attmat = []

        for key, value in product_description.items():
            value = value.strip()

            if key in self.ALL_RULES and value:
                translated_status = self.ALL_RULES[key].get(value)

                if translated_status:
                    attmat.append(translated_status)

            elif key == 'დანიშნულება' and value and value != ' ':
                attmat.append(f"დანიშნულება: {value}")

        return attmat

    def build_final_result(self, merchanttable: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes a list of material records (merchanttable) to fetch and
        translate attributes for each item, returning the final structured list.
        """
        final_result: List[Dict[str, Any]] = []

        for item in merchanttable:
            material_name = item.get('NAM_MAT')

            raw_attribute = self.get_material_attribute(material_name)

            translated_attributes: List[str] = []

            if raw_attribute:
                translated_attributes = self.translate_attributes(raw_attribute)

            result_item = {
                'NAM_MAT': material_name,
                'ID': item.get('ID'),
                'ATT_MAT_RAW': raw_attribute,
                'translated_attributes': translated_attributes,
            }

            final_result.append(result_item)

        return final_result