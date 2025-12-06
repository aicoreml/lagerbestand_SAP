# SAP Lagerbestandsprognose System

Dieses Projekt ist eine webbasierte Anwendung zur Verwaltung von Lagerbeständen mit SAP-ähnlichen Daten und Funktionen, die die Funktionalität von SAP ERP-Modulen für das Lagermanagement simuliert und Prognosefunktionen beinhaltet.

## Funktionen

- Echtzeit-Lagerdashboard
- Kategoriefilterung mit Dropdown
- Prognosefunktionen für zukünftigen Bedarf
- KI-gestützte Analyse mit Ollama
- SAP-ERP Tabellenreferenz
- CSV-Import-Funktionalität
- SAP-ähnliche Datenstruktur mit 300 Einträgen, generiert mit Faker
- **NEU**: Klickbare Dashboard-Elemente für "Gefährdete Artikel" und "Artikel mit niedrigem Bestand", die detaillierte Ansichten in neuen Tabs öffnen
- **NEU**: Nur-Prognose-Diagramm, das auf Produktauswahl in der Kategorie-Dropdown reagiert
- **NEU**: Direkter Datenpfad-Fix, um konsistenten Datenbankzugriff zu gewährleisten

## Installation und Setup

### Voraussetzungen

- Python 3.8+
- Ollama (für KI-Analyse)

### Installationsschritte

1. Repository klonen:
   ```bash
   git clone <repository-url>
   cd lagerbestand_SAP
   ```

2. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   ```

3. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

4. Ollama installieren und starten:
   - Installationsanleitung unter https://ollama.ai/
   - Ein Modell für die KI-Analyse herunterladen:
     ```bash
     ollama pull llama3
     # oder ein anderes unterstütztes Modell
     ```

5. Beispieldaten generieren:
   ```bash
   python generate_sap_data.py
   ```

6. Anwendung starten:
   ```bash
   python app_lager_sap.py
   ```

7. Zugriff auf die Anwendung unter `http://localhost:5020` (oder dem konfigurierten Port)

## Verwendung

### Dashboard-Funktionen

- **Lagerübersicht**: Alle Produkte mit aktuellen Bestandsmengen und Statusanzeigen anzeigen
- **Kategoriefilterung**: Lager nach Kategorien filtern
- **Prognosegenerierung**: Bedarfsprognosen mit anpassbaren Parametern generieren
- **KI-Analyse**: KI-gestützte Interpretation der Lagerdaten erhalten
- **Datenimport**: CSV-Dateien hochladen, um Bestandsdaten zu aktualisieren
- **NEU**: Klickbare "Gefährdete Artikel" und "Artikel mit niedrigem Bestand" Karten, die detaillierte Ansichten in neuen Browser-Tabs öffnen
- **NEU**: Nur-Prognose-Diagramm, das die Prognosedaten für ausgewählte Produkte aus dem Kategorie-Dropdown anzeigt

### Dokumentation der neuen Funktionen

#### Klickbare Dashboard-Elemente
- Die "Gefährdete Artikel" Karte kann angeklickt werden, um einen neuen Tab zu öffnen, der alle Artikel zeigt, bei denen der aktuelle Bestand unter dem Mindestbestand liegt
- Die "Artikel mit niedrigem Bestand" Karte kann angeklickt werden, um einen neuen Tab zu öffnen, der alle Artikel zeigt, bei denen der Bestand unter 50% des Sollbestands liegt, aber noch über dem Minimum ist
- Sowohl die einzelnen Zählerzahlen als auch die Kartenbereiche sind zum einfacheren Zugriff klickbar

#### Produktselektion Diagramm
- Der "Nachfrageprognose" Bereich enthält eine hierarchische Kategorie/Produkt-Auswahl
- Wählen Sie Produkte aus verschiedenen Kategorien aus, um deren Prognosedaten im Diagramm zu sehen
- Das Diagramm zeigt nur Prognosedaten für die ausgewählten Produkte an
- Nachdem Prognosen generiert wurden, aktualisiert sich das Diagramm, um die neuen Prognosedaten für ausgewählte Produkte anzuzeigen

### Datengenerierung und -verwaltung
- Das System generiert 300 Beispiel-Lagerdatensätze und 21.000 Bedarfsdatensätze beim Ausführen von `generate_sap_data.py`
- Der Datenbankpfad ist nun festgelegt, um konsistenten Zugriff unabhängig vom Ausführungskontext zu gewährleisten
- Das System enthält Sicherheitsvorkehrungen und Fehlerbehandlung für alle Operationen

### SAP ERP Integration

Die Anwendung enthält eine Referenztabelle zur Zuordnung von Dashboard-Feldern zu SAP ERP-Tabellen:

| Dashboard-Feld | SAP Tabelle | SAP Feld | Beschreibung |
|----------------|-------------|----------|--------------|
| Produkt-ID | MARA | MATNR | Materialnummer aus Materialstammsatz |
| Name | MARA | MAKTX | Material Kurztext aus Materialstammsatz |
| Kategorie | MARA | MATKL | Materialgruppe aus Materialstammsatz |
| Aktueller Bestand | MARD | LABST | Lagerbestand im Lagerort |
| Zielbestand | MARD | PLSTG | Planbestand im Lagerort |
| Mindestbestand | MARA | BVMEH | Bewirtschaftungseinheit aus Materialstammsatz |
| Maximalbestand | MARA | MAXL | Maximalbestand aus Materialstammsatz |
| Durchschn. monatl. Bedarf | MBEW | AVMBM | Durchschnittlicher Verbrauch/Monat aus Materialbewertung |
| Lieferzeit in Tagen | MARC | BESKZ | Beschaffungsart und Lieferzeit aus Werkstammsatz |
| Letzter Warenzugang | MSEG | BUDAT | Buchungsdatum Materialbewegung |
| Historische Nachfrage | S091 | DATUV, WDAT, LGMNG | Historische Daten für Prognose aus APO |
| Prognose | S092 | PERIV, WDAT, LGMNG | Prognosewerte aus APO |

## Dateistruktur

- `app_lager_sap.py`: Haupt-Flask-Anwendung mit Benutzeroberfläche und API-Endpunkten
- `generate_sap_data.py`: Skript zur Erstellung SAP-ähnlicher Beispieldaten
- `requirements.txt`: Python-Abhängigkeiten
- `sap_inventory.db`: SQLite-Datenbank (wird automatisch generiert)

## Mitwirken

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Nehmen Sie Ihre Änderungen vor
4. Führen Sie Commit durch (`git commit -m 'Add some AmazingFeature'`)
5. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
6. Öffnen Sie einen Pull Request

## Lizenz

Dieses Projekt ist unter der MIT Lizenz - siehe die [LICENSE](LICENSE) Datei für Details.