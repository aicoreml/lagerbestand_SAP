# Architektur des SAP Lagerbestand Management Systems

## Systemübersicht

Das SAP Lagerbestand Management System ist eine webbasierte Anwendung, die eine Schnittstelle für die Verwaltung von Lagerbeständen bietet und dabei SAP-ähnliche Datenstrukturen und Prozesse simuliert. Die Anwendung kombiniert Backend-Logik mit einer interaktiven Frontend-Oberfläche und integriert KI-gestützte Analysefunktionen.

## Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Web-Oberfläche)                    │
├─────────────────────────────────────────────────────────────────┤
│  - HTML, CSS (Tailwind), JavaScript                           │
│  - Chart.js für Visualisierungen                              │
│  - Interaktive Dashboard-Elemente                              │
│  - Kategorie-Filterung und Produktselektion                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API-Schnittstelle (Flask)                   │
├─────────────────────────────────────────────────────────────────┤
│  - RESTful Endpunkte für alle Funktionen                       │
│  - CRUD-Operationen für Inventardaten                          │
│  - Prognose-Generierungs-API                                   │
│  - KI-Interpretations-API                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Python Flask)                      │
├─────────────────────────────────────────────────────────────────┤
│  - Flask Web Framework                                          │
│  - Flask-CORS für Cross-Origin-Ressourcen                     │
│  - Datenbankzugriff mit SQLite3                               │
│  - Datenverarbeitung mit Pandas und NumPy                     │
│  - KI-Integration mit Ollama                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Datenbank (SQLite)                          │
├─────────────────────────────────────────────────────────────────┤
│  - inventory: Produktdaten, Bestände, Schwellwerte            │
│  - historical_demand: Historische Nachfragedaten               │
│  - forecasts: Prognosewerte und Konfidenzniveaus               │
└─────────────────────────────────────────────────────────────────┘
```

## Technologiestack

### Backend-Technologien
- **Python 3.8+**: Hauptprogrammiersprache
- **Flask**: Web-Framework für die API und Server
- **Flask-CORS**: Unterstützung für Cross-Origin Resource Sharing
- **SQLite**: Eingebettete Datenbank für Datenspeicherung
- **Pandas**: Datenanalyse und -manipulation
- **NumPy**: Numerische Berechnungen
- **Ollama**: Integration von KI-Modellen
- **scikit-learn**: Maschinelles Lernen für Prognosen
- **Faker**: Generierung von SAP-ähnlichen Testdaten

### Frontend-Technologien
- **HTML5**: Struktur der Webseiten
- **Tailwind CSS**: Styling und Responsive Design
- **JavaScript**: Interaktive Elemente und API-Abfragen
- **Chart.js**: Diagramme und Visualisierungen
- **Font Awesome**: Icon-Satz
- **Date-FNS-Adapter**: Datumshandling für Chart.js

### Abhängigkeiten
- Flask==2.3.3
- Flask-CORS==4.0.0
- pandas==2.2.3
- numpy==1.26.0
- requests==2.31.0
- scikit-learn==1.5.0
- ollama==0.1.8
- Faker==18.3.1

## Datenbankstruktur

### inventory Tabelle
| Spalte | Datentyp | Beschreibung |
|--------|----------|--------------|
| id | INTEGER | Primärschlüssel, autoincrement |
| product_id | TEXT | Eindeutige Produkt-ID (entspricht MATNR in SAP) |
| product_name | TEXT | Produktname (entspricht MAKTX in SAP) |
| category | TEXT | Produktkategorie |
| kategorie | TEXT | Alternative Kategorie (Standard: "Allgemein") |
| current_stock | INTEGER | Aktueller Lagerbestand |
| target_stock | INTEGER | Ziel-Lagerbestand |
| min_stock | INTEGER | Minimaler Bestand |
| max_stock | INTEGER | Maximaler Bestand |
| avg_monthly_demand | REAL | Durchschnittlicher monatlicher Bedarf |
| lead_time_days | INTEGER | Lieferzeit in Tagen |
| last_restock_date | DATE | Datum des letzten Warenzugangs |
| seasonality_factor | REAL | Saisonalitätsfaktor |

### historical_demand Tabelle
| Spalte | Datentyp | Beschreibung |
|--------|----------|--------------|
| id | INTEGER | Primärschlüssel, autoincrement |
| date | DATE | Datum der Nachfrage |
| product_id | TEXT | Fremdschlüssel zu inventory |
| daily_demand | INTEGER | Tägliche Nachfrage |
| price | REAL | Produktpreis |
| marketing_spend | REAL | Marketingausgaben |
| seasonal_factor | REAL | Saisonalitätsfaktor |

### forecasts Tabelle
| Spalte | Datentyp | Beschreibung |
|--------|----------|--------------|
| id | INTEGER | Primärschlüssel, autoincrement |
| product_id | TEXT | Fremdschlüssel zu inventory |
| forecast_date | DATE | Prognosedatum |
| predicted_demand | REAL | Vorhergesagter Bedarf |
| confidence_level | REAL | Konfidenzniveau |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

## API-Endpunkte

### Hauptseite
- **GET /** - Hauptdashboard mit allen Funktionen

### Inventar-APIs
- **GET /api/inventory** - Alle Inventardaten abrufen
- **GET /api/inventory/<product_id>** - Einzelnes Inventarelement abrufen
- **PUT /api/inventory/<product_id>** - Einzelnes Inventarelement aktualisieren
- **GET /api/inventory/stats** - Inventarstatistiken abrufen

### Nachfrage-APIs
- **GET /api/demand/<product_id>** - Historische Nachfrage für Produkt
- **GET /api/historical_demand_all** - Alle historischen Nachfragedaten

### Prognose-APIs
- **GET /api/forecasts** - Alle Prognosedaten abrufen
- **GET /api/forecasts/<product_id>** - Prognose für spezifisches Produkt
- **POST /api/generate_forecasts** - Neue Prognosen generieren

### KI- und Analyse-APIs
- **POST /api/interpret_results** - KI-Analyse der Ergebnisse
- **POST /api/optimize_inventory** - Lageroptimierung

### Sonstige APIs
- **POST /api/clear_forecasts** - Prognosedaten löschen
- **POST /api/upload_inventory** - Inventardaten aus CSV hochladen

## SAP ERP Integration

### Tabellenreferenz
Die Anwendung enthält eine Zuordnung zwischen Dashboard-Feldern und SAP ERP-Tabellen:

- **MARA** (Materialstamm): MATNR (Materialnummer), MAKTX (Material Kurztext), MATKL (Materialgruppe)
- **MARD** (Lagerbestand): LABST (Lagerbestand), PLSTG (Planbestand)
- **MBEW** (Materialbewertung): AVMBM (Durchschnittlicher Verbrauch/Monat)
- **MARC** (Werkstammsatz): BESKZ (Beschaffungsart und Lieferzeit)
- **MSEG** (Materialbewegung): BUDAT (Buchungsdatum)
- **S091/S092** (APO Prognosen): Historische und Prognosedaten

## Sicherheitsaspekte

- CORS-Konfiguration für sicheren API-Zugriff
- Eingabevalidierung bei CSV-Upload
- Keine direkten SQL-Befehle (stattdessen parametrisierte Abfragen)
- Keine sensible Information in den Commits (durch .gitignore geschützt)

## Skalierbarkeit und Wartung

- Modulare Architektur mit separaten Funktionen
- Klare Trennung von Frontend und Backend
- Ausführliche Dokumentation im Code
- Standardisierte Python- und JavaScript-Praktiken
- Verwendung von virtuellen Umgebungen für Abhängigkeiten