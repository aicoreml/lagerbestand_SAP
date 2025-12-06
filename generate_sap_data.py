from faker import Faker
fake = Faker('de_DE')
from faker import Faker  
import pandas as pd  
import random  
import sqlite3  
from datetime import datetime, timedelta  
import numpy as np  
  
# Initialize Faker with German locale  
fake = Faker('de_DE') 
import pandas as pd  
import random  
import sqlite3  
from datetime import datetime, timedelta  
import numpy as np  
  
def generate_sap_data(num_entries=300):
    # Generate SAP-like sample data using faker
    # Common SAP material types (MTART)
    MATERIAL_TYPES = ['FERT', 'HALB', 'ROH', 'HIBE', 'DIEN', 'FREM']
    # Realistic German material groups (MATKL) with meaningful names
    MATERIAL_GROUPS = [
        'Elektronik', 'Möbel', 'Bürobedarf', 'Maschinen',
        'Zubehör', 'Werkzeuge', 'Prüfgeräte', 'Transport'
    ]

    # Realistic German product names
    GERMAN_PRODUCTS = [
        'Laptop Computer', 'Bürostuhl ergonomisch', 'Tischlampe LED', 'Kopfhörer kabellos',
        'Maus kabellos', 'Tastatur mechanisch', 'Monitor 24 Zoll', 'Drucker Laser',
        'Scanner Farbe', 'Kopierer A4', 'Bürobedarf Set', 'Ordner A4',
        'Hefter schwarz', 'Bleistift 2B', 'Kugelschreiber', 'Notizblock A5',
        'Heft DIN A4', 'Radiergummi', 'Lineal 30cm', 'Zirkel komplett',
        'Tintenpatrone schwarz', 'Tintenpatrone farbe', 'Papier A4 80g',
        'Schreibmappen', 'Hängeordner', 'Präsentationsblock', 'Whiteboard 60x40cm',
        'Whiteboardmarker', 'Tafelkreide', 'Bücherregal', 'Schreibtisch Holz',
        'Bürostuhl höhenverstellbar', 'Bürocontainer', 'Papierkorb', 'Büroleuchte',
        'Schreibtischunterlage', 'Kalender', 'Stempelkissen', 'Brieföffner',
        'Aktenvernichter', 'Plastikmappe', 'Klemmbrett', 'Klemmleiste',
        'Tischrechner', 'Stempel Set', 'Stempelkasten', 'Karteikasten',
        'Laminiergerät', 'Laminierfolie', 'Bindesystem', 'Spiralbindung',
        'Heftzubehör', 'Füllhalter', 'Tintenpatrone blau', 'Tusche schwarz',
        'Aquarellfarben', 'Pinsel Set', 'Zeichenpapier', 'Zeichenblock',
        'Grundierung weiß', 'Farbroller', 'Farbwanne', 'Tapete', 'Tapetenkleber',
        'Klebeband 10m', 'Klebestift', 'Flüssigkleber', 'Heißklebepistole',
        'Schraubenset', 'Inbusschlüssel', 'Schraubenzieher Set', 'Hammer',
        'Zange kombiniert', 'Werkzeugkoffer', 'Winkelmesser', 'Maßband 5m',
        'Wasserwaage 60cm', 'Schutzbrille', 'Handschuhe Arbeit', 'Ohrenschützer',
        'Sicherheitsschuhe', 'Staubmaske', 'Feuerlöscher', 'Notfallkoffer',
        'Erste-Hilfe-Kasten', 'Warnweste', 'Sicherheitskette', 'Sicherheitsschlösser',
        'Sicherheitskabel', 'Sicherheitsvorhang', 'Werkstattboden', 'Ölabsorber',
        'Ölfilter', 'Luftfilter', 'Scheibenwischer', 'Reifen Sommer',
        'Reifen Winter', 'Bremsscheiben', 'Kupplungssatz', 'Zündkerzen',
        'Zündkabel', 'Batterie 12V', 'Bremssattel', 'Kupplungsseil',
        'Stoßdämpfer', 'Getriebeflüssigkeit', 'Bremsflüssigkeit',
        'Kühlflüssigkeit', 'Motoröl 10W40', 'Scheinwerfer', 'Rücklicht',
        'Blinker vorne', 'Blinker hinten', 'Scheinwerferlicht', 'Nebelscheinwerfer',
        'Kabelsätze', 'Lichtmaschine', 'Anlasser', 'Klimaanlage Kompressor',
        'Kühlwasserleitung', 'Auspuffanlage', 'Katalysator', 'Lambdasonde',
        'Benzinpumpe', 'Tankdeckel', 'Scheinwerfergehäuse', 'Richtungskugel',
        'Getriebestecker', 'Sensoren Set', 'Relais Standard', 'Kabelbinder',
        'Kabelmuffen', 'Steckverbinder', 'Sicherungen Set', 'Glühkerzen',
        'Glühlampen Set', 'Bodenbelag', 'Wandfarbe', 'Deckenfarbe',
        'Farbroller 18cm', 'Farbpinsel 25mm', 'Farbwanne', 'Malervlies',
        'Malerkrepp', 'Farbverdünner', 'Grundierung', 'Deckfarbe',
        'Farbtiegel', 'Malerspachtel', 'Silikon Dichtung', 'Dichtungsband',
        'Dichtungsmittel', 'Mörtel 25kg', 'Zement 25kg', 'Sand 25kg',
        'Kalk 25kg', 'Kleber Fliesen', 'Fliesenspachtel', 'Fliesenkreuz',
        'Fliesen Set 30x30cm', 'Fliesen Set 60x60cm', 'Mosaikfliesen',
        'Badezimmerfliesen', 'Küchenfliesen', 'Rutschbremse Fliesen',
        'Silikon Fliesen', 'Fliesensäge', 'Fliesenhammer', 'Fliesenzange',
        'Fliesenmeißel', 'Schleifpapier', 'Schleifvlies', 'Politur Set',
        'Wachsen Farbe', 'Nadellack', 'Decklack', 'Bleistiftlack',
        'Spraylack', 'Lackdüse', 'Lackfilter', 'Lackwischer',
        'Lackierdüse', 'Lackierzubehör', 'Verdünnungsmittel', 'Härter',
        'Füller Spachtelmasse', 'Spachtelmasse', 'Spachtel Set',
        'Schleifmaschine', 'Poliermaschine', 'Bohrmaschine',
        'Winkelschleifer', 'Tischkreissäge', 'Handkreissäge',
        'Stichsäge', 'Schraubstock', 'Schlosserbank', 'Werkbank',
        'Sägebank', 'Spannvorrichtung', 'Zentrierbohrer', 'Bohrer Set',
        'Senker', 'Gewindedüsen', 'Inbusschrauben', 'Flachkopfschrauben',
        'Senkschrauben', 'Schraubenmutter Set', 'Muttern Set',
        'Unterlegscheiben', 'Federn Set', 'Kugellager', 'Zylinderstifte',
        'Sicherungsscheiben', 'Klemmschellen', 'Kabelschellen',
        'Schlauchschläuche', 'Schlauchverbinder', 'Dichtungen Set',
        'Dichtungssätze', 'O-Ringe', 'Dichtungsmittel', 'Abdichtungsmasse',
        'Silikon Dichtung', 'Klebestreifen', 'Dichtungskordel', 'Dichtungsknete',
        'Kitt', 'Fugenmörtel', 'Fugenspachtel', 'Fugenkratzer',
        'Fugenbürste', 'Fugenstripper', 'Fugenfarbe', 'Fugenbürste Set',
        'Fliesenbürste', 'Fliesenreiniger', 'Marmoröl', 'Marmorpaste',
        'Marmorpolitur', 'Marmorversiegelung', 'Granitöl', 'Granitpolitur',
        'Granitversiegelung', 'Natursteinpflege', 'Natursteinreiniger',
        'Steinreiniger', 'Steinpflege', 'Pflegemittel Set', 'Reinigungsset',
        'Reinigungsmittel', 'Desinfektionsmittel', 'Desinfektionsmittel Set',
        'Handdesinfektion', 'Hygienetücher', 'Hygiene Set', 'Putzmittel',
        'Fensterreiniger', 'Bodenseife', 'Fettlöser', 'Schimmelentferner',
        'Kalkentferner', 'Bleichmittel', 'Waschmittel', 'Weichspüler',
        'Waschpulver', 'Waschmittel Set', 'Waschzusatz', 'Weichspüler Set',
        'Waschmittel Probiergröße', 'Waschmittel Ersatz', 'Waschmittel Nachfüll',
        'Waschmittel Flüssig', 'Waschmittel Pulver', 'Waschmittel Kapseln',
        'Waschmittel für Bunt', 'Waschmittel für Weiß', 'Waschmittel für Wolle',
        'Waschmittel für Seide', 'Waschmittel für Fein', 'Waschmittel für Hand',
        'Waschmittel für Maschine', 'Waschmittel für Kalt', 'Waschmittel für Warm',
        'Waschmittel für 30 Grad', 'Waschmittel für 40 Grad', 'Waschmittel für 60 Grad',
        'Waschmittel für 90 Grad', 'Waschmittel für Wolle', 'Waschmittel für Seide',
        'Waschmittel für Synthetik', 'Waschmittel für Misch', 'Waschmittel für Baumwolle'
    ]

    # Generate materials
    materials = []
    for i in range(num_entries):
        material_id = f"MAT{str(i+1).zfill(6)}"

        # Create material with SAP-like characteristics
        material = {
            'MATNR': material_id,  # Material number
            'MAKTX': random.choice(GERMAN_PRODUCTS),  # Realistic German product description
            'MATKL': random.choice(MATERIAL_GROUPS),  # Material group
            'MTART': random.choice(MATERIAL_TYPES),  # Material type
            'BRGEW': round(random.uniform(0.1, 50.0), 3),  # Gross weight
            'NTGEW': round(random.uniform(0.1, 45.0), 3),  # Net weight
            'GEWEI': random.choice(['KG', 'G', 'TON', 'T', 'PND']),  # Weight unit
            'MEINS': random.choice(['ST', 'M', 'C62', 'KGM', 'LTR']),  # Base unit
            'ERSDA': str(fake.date_between(start_date='-365d', end_date='today')),  # Created date
            'LAEDA': str(fake.date_between(start_date='-30d', end_date='today')),  # Last changed
            'VOREF': random.choice([True, False]),  # MRP indicator
            'DISPO': random.choice(['PD', 'MP01', 'MP02', 'MP03']),  # MRP type
            'PLANNING_FACTOR': round(random.uniform(0.8, 1.2), 2),  # For forecasting
            'WERKS': random.choice(['1000', '2000', '3000', '4000']),  # Plant
            'DISLS': random.choice(['FV', 'PD', 'ND', 'NV']),  # MRP strategy
            'WEBAZ': random.randint(1, 14),  # GR processing time
            'BESKZ': random.choice(['F', 'E']),  # Procurement type
            'PLIFZ': random.randint(0, 10),  # Planned delivery time
            'LZEIH': random.choice(['ST', 'M', 'C62']),  # Order unit
            'MABST': random.randint(10, 200),  # Min order qty
            'MAXL': random.randint(500, 5000),  # Max stock level
            'EISBE': random.randint(10, 50),  # Safety stock
            'BSTMI': random.randint(10, 100),  # Order qty
            'LGPRO': random.choice(['0001', '0002', '0003']),  # Issue storage
        }

        # Map SAP fields to application fields
        app_material = {
            'product_id': material['MATNR'],
            'product_name': material['MAKTX'],
            'category': material['MATKL'],
            'kategorie': material['MATKL'],  # Use the same value as category for now, or map based on product type
            'current_stock': random.randint(0, 300),
            'target_stock': random.randint(50, 500),
            'min_stock': random.randint(5, 50),
            'max_stock': random.randint(200, 1000),
            'avg_monthly_demand': round(random.uniform(10.0, 300.0), 1),
            'lead_time_days': random.randint(1, 30),
            'last_restock_date': str(fake.date_between(start_date='-60d', end_date='today')),
            'seasonality_factor': material['PLANNING_FACTOR']
        }

        materials.append(app_material)

    return pd.DataFrame(materials)
  
def generate_sap_demand_data(materials_df, days=70):  
    # Generate SAP-like demand data  
    demand_data = []  
  
    for _, material in materials_df.iterrows():  
        product_id = material['product_id']  
  
        for i in range(days):  
            date = fake.date_between(start_date=f'-{days}d', end_date='today')  
            demand = random.randint(0, 50)  
  
            demand_data.append({  
                'date': str(date),  
                'product_id': product_id,  
                'daily_demand': demand,  
                'price': round(random.uniform(5.0, 200.0), 2),  
                'marketing_spend': round(random.uniform(0.0, 500.0), 2),  
                'seasonal_factor': round(random.uniform(0.8, 1.2), 1)  
            })  
  
    return pd.DataFrame(demand_data)  
  
  
def create_and_populate_database():  
    # Create database and populate with SAP-like data  
    print('Creating SAP-like database with 300 entries...')  
  
    # Connect to database  
    conn = sqlite3.connect('sap_inventory.db')  
    cursor = conn.cursor()  
  
    # Drop existing tables if they exist  
    cursor.execute('DROP TABLE IF EXISTS forecasts')  
    cursor.execute('DROP TABLE IF EXISTS historical_demand')  
    cursor.execute('DROP TABLE IF EXISTS inventory')  
  
    # Create inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            kategorie TEXT DEFAULT 'Allgemein',
            current_stock INTEGER NOT NULL,
            target_stock INTEGER NOT NULL,
            min_stock INTEGER NOT NULL,
            max_stock INTEGER NOT NULL,
            avg_monthly_demand REAL NOT NULL,
            lead_time_days INTEGER NOT NULL,
            last_restock_date DATE,
            seasonality_factor REAL DEFAULT 1.0
        )
    ''')
  
    # Create historical demand table  
    cursor.execute('''  
        CREATE TABLE IF NOT EXISTS historical_demand (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            date DATE NOT NULL,  
            product_id TEXT NOT NULL,  
            daily_demand INTEGER NOT NULL,  
            price REAL,  
            marketing_spend REAL,  
            seasonal_factor REAL DEFAULT 1.0,  
            FOREIGN KEY (product_id) REFERENCES inventory (product_id)  
        )  
    ''')  
  
    # Create forecast table  
    cursor.execute('''  
        CREATE TABLE IF NOT EXISTS forecasts (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            product_id TEXT NOT NULL,  
            forecast_date DATE NOT NULL,  
            predicted_demand REAL NOT NULL,  
            confidence_level REAL DEFAULT 0.95,  
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
            FOREIGN KEY (product_id) REFERENCES inventory (product_id)  
        )  
    ''')  
  
    # Generate SAP-like data  
    print('Generating SAP-like inventory data...')  
    sap_inventory = generate_sap_data(300)  # 300 entries as requested  
    print(f'Generated {len(sap_inventory)} inventory records')  
  
    print('Generating SAP-like demand data...')  
    sap_demand = generate_sap_demand_data(sap_inventory, 70)  # 70 days of demand  
    print(f'Generated {len(sap_demand)} demand records')  
  
    # Insert data into database  
    print('Inserting data into database...')  
    sap_inventory.to_sql('inventory', conn, if_exists='append', index=False)  
    sap_demand.to_sql('historical_demand', conn, if_exists='append', index=False)  
  
    conn.commit()  
    conn.close()  
  
    print('Database creation and population completed!')  
    print(f'Total inventory records: {len(sap_inventory)}')  
    print(f'Total demand records: {len(sap_demand)}')  
  
  
if __name__ == '__main__':  
    create_and_populate_database() 
