import pandas as pd
from typing import List, Dict, Any
from io import StringIO
from database import Database
db = Database()


# from database import Database # Uncomment if using a live database

class MaterialAttributeTranslator:
    """
    A class to fetch and translate the compressed ATT_MAT string
    from a material record into a list of human-readable attributes.
    """

    # --- 0. STATIC LOOKUP DATA (Embedded) ---
    _MATFORM_CONTENT = """cod_form,nam_form
1.0,"აბი,დრაჟე,კაფსულა,ფხვნილი,ცხიმ"
2.0,"ამპულები, ფლაკონები(სტერილური)"
3.0,გალენური ფორმები გარეგნ ხსნარი
4.0,"მალამო, კრემი, ჟელე, პასტა, სანთ."
5.0,რეზინის და პლასტმასის ნაწარმი
6.0,მცენარეული ფორმები
7.0,სამედიცინო ტექნიკ.ნაკეთობა(ა)
8.0,შესახვევი მასალები
9.0,ინფუზიური ხსნარები
10.0,"სტომატოლოგია:მასალები,ინსტრუმ."
11.0,"აეროზოლები, ინჰალატორები"
12.0,პირადი ჰიგიენის საგნები
13.0,ბავშვთა კვება
14.0,ბავშვთა აქსესუარები
15.0,"სარეცეპტუროს ჭურჭელი, მასალები"
16.0,მაცივარში და გრილ ადგილას
17.0,საყოფაცხოვრებო მოხმარების საგნ
18.0,სამედიცინო დანიშნულ თეთრეული
19.0,"პოლიგრაფიული,სარეკლამო ნაწარმი"
20.0,სამედიცინო ტექ.ნაკეთობა(ბ)
21.0,კვების პროდუქტები"""

    _MATSTOR_CONTENT = """cod_stor,nam_stor
0.0,შეუზღუდავი
1.0,მაცივარში
2.0,გრილი
3.0,მშრალი
4.0,გრილი მშრალი
5.0,მშრალ ადგილზე <20 გრ.C
6.0,მშრალ ადგილზე 15-20 გრ.C
7.0,მშრალ ადგილზე 2-15 გრ.C"""

    _SAXEEBI_CONTENT = """cod_saxe,nam_saxe,cod_form
1.0,ტაბლეტი,1.0
2.0,ტაბლეტი საღეჭი,1.0
3.0,ტაბლეტი შუშხუნა,1.0
4.0,კაფსულა,1.0
5.0,მიკროკაფსულა,1.0
6.0,ფხვნილი შინაგანი,1.0
7.0,ფხვნილი გარეგანი,1.0
8.0,ფხვნ.ლიოფილიზირ,1.0
9.0,მედ/ნედლეული,1.0
10.0,ინპლანტანტი,1.0
11.0,გრანულა,1.0
12.0,დრაჟე,1.0
13.0,მიკროდრაჟე,1.0
14.0,კაპლეტი,1.0
15.0,ნაყენი,3.0
16.0,ხსნარი წყლიანი,3.0
17.0,ხს.სპირტ.გარეგანი,3.0
18.0,ხს.გლიცერინიანი,3.0
19.0,ხსნარი ზეთოვანი,2.0
20.0,სიროფი,3.0
21.0,წვენი,3.0
22.0,ექსტრაქტ.სქელი,3.0
23.0,ექსტრაქტ.მშრალი,3.0
24.0,ექსტრაქტ.სითხოვანი,3.0
25.0,ექსტრ.ზეთოვანი,3.0
26.0,საკ/დანამატი,1.0
27.0,სუსპ.ორალური,3.0
28.0,სუსპ.საინექციო,2.0
29.0,ელექსირი,3.0
30.0,ემულსია,3.0
31.0,ფხვნილი სტერილ.,2.0
32.0,ხს.საინექ.ამპულ,2.0
33.0,ხს.საინექ.ფლ.,2.0
34.0,ხს.ინფუზიური,9.0
35.0,მალამო,4.0
36.0,სუპოზიტორია,4.0
37.0,ლინიმენტი,4.0
38.0,კრემი,4.0
39.0,ჟელე გარეგ.,4.0
40.0,პასტა,4.0
41.0,ემპლასტრო,1.0
42.0,თვალის წვეთები,2.0
43.0,თვალის მალამო,4.0
44.0,თვალ.ფირფიტები,5.0
45.0,ცხვ.ყურის წვ.,2.0
46.0,ტაბლეტი საწ.,1.0
47.0,კარამელი სამკ.,1.0
48.0,მც/ნაკრები,6.0
49.0,ბრიკეტი,6.0
50.0,ს/მცენარე,6.0
51.0,ს/ჩაი,6.0
52.0,"აეროზოლი, სპრეი",11.0
53.0,ავად.მოვ/საგ.,5.0
54.0,პირადი ჰიგ.საგ.,12.0
55.0,ბავშვთა კვება,13.0
56.0,ბ/აქსესუარები,14.0
57.0,შესახვევი მასალ,5.0
58.0,მედ.ტექნიკა,5.0
60.0,საყოფაც.მოხ.საგ,5.0
61.0,სტომატოლოგია,10.0
62.0,ხს.ორალური ფლ,2.0
63.0,ხს.საინ.კარპულა,2.0
64.0,ჟელე შინაგანი,1.0
65.0,ხს.საპნ.შამპუნი,12.0
66.0,ხს.სპირტ.შინაგ.,3.0
67.0,პლასტირი თხევად,5.0
68.0,პლასტირი,5.0
69.0,მიქსტურა,3.0
70.0,პოლიგრაფ.ნაწარმი,19.0
71.0,კვების პროდუქტ.,21.0
72.0,სამ.ელასტ.ნაწარმ,20.0
73.0,ომრონის პროდუქ.,20.0
74.0,რეზინის ნაწარმი,5.0
75.0,სარეკლამო ბრენდ,19.0
76.0,ბავშვთა მოვლა,14.0
77.0,თმის მოვლა,12.0
78.0,საკვები ზეთი,21.0
79.0,სასაჩუქრო ბარათი,19.0
103.0,სარეგისტრაციო ნ,19.0
104.0,კოლოფი,1.0
105.0,ხსნარი ზეთოვანი,3.0
106.0,სხვა საკვები,21.0
108.0,ცხოველთა მოვლა,1.0"""

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
        'დანიშნულება': {'0': 'არ არის დანიშნულება', '1': 'გაიცემა დანიშნულებით'}
    }

    EXAMPLE_ATT_MAT_STRING = "0100200000111000"

    def __init__(self):


        self.MATFORM_MAP = self._create_lookup_map_from_string(self._MATFORM_CONTENT, 'cod_form', 'nam_form')
        self.MATSTOR_MAP = self._create_lookup_map_from_string(self._MATSTOR_CONTENT, 'cod_stor', 'nam_stor')
        self.SAXEEBI_MAP = self._create_lookup_map_from_string(self._SAXEEBI_CONTENT, 'cod_saxe', 'nam_saxe')

        self.ALL_RULES: Dict[str, Dict[str, str]] = {
            'ფორმების კოდი': self.MATFORM_MAP,
            'მაცივარიში შენახვის პირობები': self.MATSTOR_MAP,
            'გამოშვების სახე': self.SAXEEBI_MAP,
            **self._SIMPLE_RULES
        }

    def _create_lookup_map_from_string(self, content: str, code_col: str, name_col: str) -> Dict[str, str]:
        # ... (Implementation remains the same) ...
        try:
            df = pd.read_csv(StringIO(content))
            df['code_str'] = pd.to_numeric(df[code_col], errors='coerce').fillna(0).astype(int).astype(str)
            return df.set_index('code_str')[name_col].to_dict()
        except Exception:
            return {}

    def get_material_attribute(self,material_name: str) -> str | None:
        """Fetches the ATT_MAT string for a given material name."""
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT
                        "ATT_MAT"
                    FROM
                        public.mater1
                    WHERE
                        "NAM_MAT" = %s;
                    """,
                                   (material_name,)
                                   )
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        return None

        except Exception as e:
            print(f"Database error while fetching attribute: {e}")
            # --- PLACEHOLDER RETURN ---
            # Returns the test string if the database connection fails
            # so the rest of the parsing logic can be tested.


    def translate_attributes(self, attribute_value_str: str) -> List[str]:
        # ... (Implementation remains the same - the core parsing logic) ...
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

    # -------------------------------------------------------------------
    # NEW METHOD TO BUILD FINAL RESULT LIST
    # -------------------------------------------------------------------
    def build_final_result(self, merchanttable: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes a list of material records (merchanttable) to fetch and
        translate attributes for each item, returning the final structured list.
        """
        final_result: List[Dict[str, Any]] = []

        for item in merchanttable:
            material_name = item.get('NAM_MAT')

            # 1. Fetch the raw attribute string
            raw_attribute = self.get_material_attribute(material_name)

            translated_attributes: List[str] = []

            if raw_attribute:
                # 2. Translate the raw string into a list of descriptions
                translated_attributes = self.translate_attributes(raw_attribute)

            # 3. Build the final result dictionary
            result_item = {
                'NAM_MAT': material_name,
                'ID': item.get('ID'),
                'ATT_MAT_RAW': raw_attribute,
                'translated_attributes': translated_attributes,
            }

            final_result.append(result_item)

        return final_result


# -------------------------------------------------------------------
# EXAMPLE USAGE IN YOUR MAIN SCRIPT
# -------------------------------------------------------------------

# # Assume this part is in your main file (e.g., merchant_processor.py)

# from att_mat import MaterialAttributeTranslator
# from typing import List, Dict, Any

# Mock Data (replace with your actual table data)
# merchanttable = [ ... ]
# merchanttable = [
#     {'NAM_MAT': 'Aspirin 500mg', 'ID': 101},
#     {'NAM_MAT': 'Tylenol 200mg', 'ID': 102},
#     {'NAM_MAT': '5-ნიტროქსი 0.05გ #80ტ', 'ID': 103},
# ]

# 1. Initialize the translator instance
# Pass your database instance here if available: translator = MaterialAttributeTranslator(db_instance=db)
# translator = MaterialAttributeTranslator()

# 2. Call the new method to build the final list
# final_result = translator.build_final_result(merchanttable)

# 3. Verification/Output
# print("\n--- Final Result List Built by Translator Class ---")
# for result in final_result:
#     print(f"Material: {result['NAM_MAT']}")
#     print(f"  ID: {result['ID']}")
#     print(f"  Raw ATT: {result['ATT_MAT_RAW']}")
#     print(f"  Translated Attributes: {result['translated_attributes']}")