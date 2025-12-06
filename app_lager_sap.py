from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import ollama

app = Flask(__name__)
CORS(app)

# Database setup
import os
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sap_inventory.db')

def init_db():
    """Initialize the database with sample data."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create inventory table if it doesn't exist
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

    # Add Kategorie column if it doesn't exist (for backward compatibility with existing databases)
    try:
        cursor.execute("ALTER TABLE inventory ADD COLUMN kategorie TEXT DEFAULT 'Allgemein'")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Create historical demand table if it doesn't exist
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

    # Create forecast table if it doesn't exist
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

    # Load sample data only if tables are empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    count_result = cursor.fetchone()[0]
    if count_result == 0:
        if os.path.exists('sample_inventory_data_german_utf8.csv'):
            sample_inventory = pd.read_csv('sample_inventory_data_german_utf8.csv', encoding='utf-8')
            # Only take first 5 products
            sample_inventory = sample_inventory.head(5)
            first_five_product_ids = sample_inventory['product_id'].tolist()
            sample_inventory.to_sql('inventory', conn, if_exists='append', index=False)

            if os.path.exists('historical_demand_data_german_full.csv'):
                sample_demand = pd.read_csv('historical_demand_data_german_full.csv')
                # Filter demand data to only include products that are actually in inventory
                sample_demand = sample_demand[sample_demand['product_id'].isin(first_five_product_ids)]
                sample_demand.to_sql('historical_demand', conn, if_exists='append', index=False)
    else:
        print(f"Database already has {count_result} inventory records, skipping sample data import")

    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main page."""
    html_content = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lagerbestandsprognose</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold text-center text-gray-800 mb-8">Lagerbestandsprognose</h1>

            <div class="mb-8 bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-xl font-bold mb-4">Kategorien filtern</h2>
                <div class="flex flex-wrap items-center gap-2">
                    <label for="categorySelect" class="text-gray-700 font-medium">Kategorie wählen:</label>
                    <select id="categorySelect" class="border rounded p-2 bg-white">
                        <option value="all">Alle Kategorien</option>
                    </select>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="flex items-center">
                        <div class="p-3 rounded-full bg-blue-100 mr-4">
                            <i class="fas fa-boxes text-blue-500 text-xl"></i>
                        </div>
                        <div>
                            <p class="text-gray-600">Gesamtprodukte</p>
                            <p id="totalProducts" class="text-2xl font-bold">0</p>
                        </div>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-lg shadow-md cursor-pointer hover:shadow-lg transition-shadow" onclick="window.open('/at-risk-items', '_blank')">
                    <div class="flex items-start">
                        <div class="p-3 rounded-full bg-red-100 mr-4 mt-1">
                            <i class="fas fa-chart-line text-red-500 text-xl"></i>
                        </div>
                        <div>
                            <p class="text-gray-600">Gefährdete Artikel</p>
                            <div id="atRiskItems" class="text-2xl font-bold">0</div>
                        </div>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-lg shadow-md cursor-pointer hover:shadow-lg transition-shadow" onclick="window.open('/low-stock-items', '_blank')">
                    <div class="flex items-start">
                        <div class="p-3 rounded-full bg-yellow-100 mr-4 mt-1">
                            <i class="fas fa-exclamation-triangle text-yellow-500 text-xl"></i>
                        </div>
                        <div>
                            <p class="text-gray-600">Artikel mit niedrigem Bestand</p>
                            <div id="lowStockItems" class="text-2xl font-bold">0</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-bold">Lagerstatus</h2>
                        <button id="downloadInventoryBtn" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
                            Lagerstatus als CSV herunterladen
                        </button>
                    </div>
                    <div class="overflow-x-auto max-h-96 overflow-y-auto">  <!-- Add height restriction and scrollbar -->
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50 sticky top-0 z-10">  <!-- Sticky header -->
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produkt-ID</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kategorie</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aktueller Bestand</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Zielbestand</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Letzte Warenzugang</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody id="inventoryTableBody" class="bg-white divide-y divide-gray-200">
                                <tr>
                                    <td colspan="7" class="text-center">Lade Daten...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h2 class="text-xl font-bold mb-4">Nachfrageprognose</h2>
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Kategorie und Produkt(e) wählen:</label>
                        <div id="categoryProductContainer" class="border rounded p-3 max-h-60 overflow-y-auto">
                            <!-- Categories and products will be dynamically generated here -->
                            <div class="text-sm text-gray-500">Lade Kategorien...</div>
                        </div>
                        <div class="mt-2 text-sm text-gray-600">
                            Wählen Sie eine Kategorie aus, um die zugehörigen Produkte zu sehen. Dann wählen Sie die Produkte aus, für die Sie die Nachfrageprognose anzeigen möchten.
                        </div>
                    </div>
                    <div class="h-80">
                        <canvas id="demandChart"></canvas>
                    </div>
                </div>
            </div>

            <div class="mt-8 bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-xl font-bold mb-4">Prognose generieren</h2>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div>
                        <div class="flex flex-wrap items-center gap-4 mb-4">
                            <div class="flex flex-col">
                                <label for="forecastCategorySelect" class="text-sm text-gray-600 mb-1">Kategorie wählen (optional):</label>
                                <select id="forecastCategorySelect" class="border rounded p-2">
                                    <option value="">Alle Kategorien</option>
                                </select>
                            </div>

                            <button id="forecastBtn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-5">  <!-- Added mt-5 to align with dropdown -->
                                Prognosen generieren
                            </button>

                            <div class="flex flex-col">
                                <label for="startDate" class="text-sm text-gray-600 mb-1">Startdatum</label>
                                <input type="date" id="startDate" class="border rounded p-2">
                            </div>

                            <div class="flex flex-col">
                                <label for="endDate" class="text-sm text-gray-600 mb-1">Enddatum</label>
                                <input type="date" id="endDate" class="border rounded p-2">
                            </div>

                            <div class="flex flex-col">
                                <label for="forecastDuration" class="text-sm text-gray-600 mb-1">Prognosedauer (Tage)</label>
                                <select id="forecastDuration" class="border rounded p-2">
                                    <option value="7" selected>7 Tage</option>
                                    <option value="14">14 Tage</option>
                                    <option value="30">30 Tage</option>
                                    <option value="60">60 Tage</option>
                                    <option value="90">90 Tage</option>
                                </select>
                            </div>
                        </div>

                        <div id="forecastResult" class="mt-4"></div>
                    </div>

                    <div>  <!-- Right side for forecast details -->
                        <h3 class="text-base font-semibold mb-2">Prognosedetails</h3>
                        <div class="overflow-x-auto text-sm max-h-64 overflow-y-auto">  <!-- Added smaller text and max height -->
                            <table id="forecastTable" class="min-w-full divide-y divide-gray-200 text-xs">  <!-- Smaller text -->
                                <thead class="bg-gray-50 sticky top-0">  <!-- Sticky header -->
                                    <tr>
                                        <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Prognosedatum</th>
                                        <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Produkt-ID</th>
                                        <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Vorhergesagte Nachfrage</th>
                                        <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Konfidenzniveau</th>
                                    </tr>
                                </thead>
                                <tbody id="forecastTableBody" class="bg-white divide-y divide-gray-200">
                                    <tr>
                                        <td colspan="4" class="text-center py-2">Keine Prognosedaten verfügbar</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-8 bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-xl font-bold mb-4">KI-gestützte Datenauswertung</h2>
                <button id="interpretBtn" class="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded mb-4">
                    Ergebnisse mit KI interpretieren
                </button>
                <div id="interpretResult" class="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
                    <h3 class="font-semibold mb-2">KI-Interpretation:</h3>
                    <p id="interpretationContent">Klicken Sie auf den Button, um eine KI-Interpretation zu erhalten</p>
                </div>
            </div>

            <div class="mt-8 bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-xl font-bold mb-4">SAP ERP Tabellenreferenz - Dashboard Felder</h2>
                <div class="overflow-x-auto max-h-60 overflow-y-auto">  <!-- Limit height and add scroll -->
                    <table class="min-w-full divide-y divide-gray-200 text-sm">  <!-- Added text-sm for smaller text -->
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Dashboard-Feld</th>
                                <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">SAP Tabelle</th>
                                <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">SAP Feld</th>
                                <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">Beschreibung</th>
                            </tr>
                        </thead>
                        <tbody id="sapTablesBody" class="bg-white divide-y divide-gray-200 text-sm">  <!-- Smaller text for rows -->
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="mt-8 bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-xl font-bold mb-4">Daten aktualisieren</h2>
                <div class="flex flex-col gap-4">
                    <div>
                        <label class="block text-gray-700 text-sm font-bold mb-2" for="dataFile">
                            CSV-Datei mit Inventardaten hochladen:
                        </label>
                        <input type="file" id="dataFile" accept=".csv" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                        <button id="uploadDataBtn" class="ml-2 bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
                            Daten hochladen
                        </button>
                    </div>
                    <div class="text-xs text-gray-600">  <!-- Smaller text -->
                        <p class="font-semibold">Format für Inventardaten-CSV:</p>
                        <p>Spalten: product_id, product_name, category, current_stock, target_stock, min_stock, max_stock, avg_monthly_demand, lead_time_days, last_restock_date, seasonality_factor</p>
                        <p>Beispiel: PROD001,Kabellose Kopfhörer,Electronics,45,100,20,200,85.0,5,2025-11-15,1.2</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Clear any potential cached state
                localStorage.clear();
                sessionStorage.clear();

                // Clear forecast data from the database on startup
                fetch('/api/clear_forecasts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Forecast data cleared:', data.message);

                    // Set default dates for the date inputs
                    const today = new Date();
                    const nextWeek = new Date();
                    nextWeek.setDate(today.getDate() + 7);

                    const startDateInput = document.getElementById('startDate');
                    const endDateInput = document.getElementById('endDate');

                    if (startDateInput) {
                        startDateInput.valueAsDate = today;
                    }
                    if (endDateInput) {
                        endDateInput.valueAsDate = nextWeek;
                    }

                    // Clear forecast data and graphics on startup
                    const forecastTableBody = document.getElementById('forecastTableBody');
                    if (forecastTableBody) {
                        forecastTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-2">Keine Prognosedaten verfügbar</td></tr>';
                    }

                    // Clear the demand chart if it exists
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                        window.demandChart = null;
                    }

                    // Clear any previous forecast results
                    const forecastResult = document.getElementById('forecastResult');
                    if (forecastResult) {
                        forecastResult.innerHTML = '';
                    }

                    // Load all data fresh (but don't load forecasts initially)
                    loadCategories();  // Load categories first
                    loadProductsForDropdown();  // Load products for the dropdown
                    loadInventoryData();  // Show all products initially
                    loadDashboardStats();
                    loadSapTablesReference();

                    // Load empty demand chart (without data)
                    loadDemandChart();
                    // Don't load forecast table initially, keep it empty

                    // Add event listeners only if elements exist
                    const forecastBtn = document.getElementById('forecastBtn');
                    if (forecastBtn) {
                        forecastBtn.addEventListener('click', generateForecast);
                    }

                    const interpretBtn = document.getElementById('interpretBtn');
                    if (interpretBtn) {
                        interpretBtn.addEventListener('click', interpretResults);
                    }

                    const uploadDataBtn = document.getElementById('uploadDataBtn');
                    if (uploadDataBtn) {
                        uploadDataBtn.addEventListener('click', uploadData);
                    }

                    const downloadInventoryBtn = document.getElementById('downloadInventoryBtn');
                    if (downloadInventoryBtn) {
                        downloadInventoryBtn.addEventListener('click', downloadInventoryAsCsv);
                    }
                })
                .catch(error => {
                    console.error('Fehler beim Löschen der Prognosedaten:', error);

                    // Even if the API call fails, still proceed with UI reset
                    // Set default dates for the date inputs
                    const today = new Date();
                    const nextWeek = new Date();
                    nextWeek.setDate(today.getDate() + 7);

                    const startDateInput = document.getElementById('startDate');
                    const endDateInput = document.getElementById('endDate');

                    if (startDateInput) {
                        startDateInput.valueAsDate = today;
                    }
                    if (endDateInput) {
                        endDateInput.valueAsDate = nextWeek;
                    }

                    // Clear forecast data and graphics on startup
                    const forecastTableBody = document.getElementById('forecastTableBody');
                    if (forecastTableBody) {
                        forecastTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-2">Keine Prognosedaten verfügbar</td></tr>';
                    }

                    // Clear the demand chart if it exists
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                        window.demandChart = null;
                    }

                    // Clear any previous forecast results
                    const forecastResult = document.getElementById('forecastResult');
                    if (forecastResult) {
                        forecastResult.innerHTML = '';
                    }

                    // Load all data fresh (but don't load forecasts initially)
                    loadCategories();  // Load categories first
                    loadProductsForDropdown();  // Load products for the dropdown
                    loadInventoryData();  // Show all products initially
                    loadDashboardStats();
                    loadSapTablesReference();

                    // Load empty demand chart (without data)
                    loadDemandChart();
                    // Don't load forecast table initially, keep it empty

                    // Add event listeners only if elements exist
                    const forecastBtn = document.getElementById('forecastBtn');
                    if (forecastBtn) {
                        forecastBtn.addEventListener('click', generateForecast);
                    }

                    const interpretBtn = document.getElementById('interpretBtn');
                    if (interpretBtn) {
                        interpretBtn.addEventListener('click', interpretResults);
                    }

                    const uploadDataBtn = document.getElementById('uploadDataBtn');
                    if (uploadDataBtn) {
                        uploadDataBtn.addEventListener('click', uploadData);
                    }

                    const downloadInventoryBtn = document.getElementById('downloadInventoryBtn');
                    if (downloadInventoryBtn) {
                        downloadInventoryBtn.addEventListener('click', downloadInventoryAsCsv);
                    }
                });
            });

            // Function to download chart as PNG
            async function downloadChartAsPng() {
                // Wait a bit to ensure the chart is rendered
                await new Promise(resolve => setTimeout(resolve, 100));

                const chart = window.demandChart;
                if (chart) {
                    // Get the chart's canvas
                    const canvas = chart.canvas;
                    if (canvas) {
                        // Get high-resolution image
                        const originalWidth = canvas.width;
                        const originalHeight = canvas.height;

                        // Increase resolution for better quality
                        const width = originalWidth * 2;
                        const height = originalHeight * 2;

                        const temporaryCanvas = document.createElement('canvas');
                        temporaryCanvas.width = width;
                        temporaryCanvas.height = height;

                        const temporaryCtx = temporaryCanvas.getContext('2d');
                        temporaryCtx.scale(2, 2);

                        // Draw the original canvas to the temporary canvas
                        temporaryCtx.drawImage(canvas, 0, 0);

                        const url = temporaryCanvas.toDataURL('image/png');

                        // Create a temporary link to download the image
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = 'Nachfrageprognose_' + new Date().toISOString().slice(0, 10) + '.png';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    } else {
                        alert('Kein Diagramm-Canvas gefunden');
                    }
                } else {
                    alert('Kein Diagramm zum Herunterladen verfügbar');
                }
            }

            // Function to download forecast table as CSV
            function downloadForecastAsCsv() {
                const tableBody = document.getElementById('forecastTableBody');
                if (!tableBody) {
                    alert('Keine Prognosedaten zum Herunterladen verfügbar');
                    return;
                }

                // Get all rows from the table body
                const rows = tableBody.querySelectorAll('tr');
                if (rows.length === 0 || (rows.length === 1 && rows[0].querySelector('td').textContent.includes('Keine Prognosedaten'))) {
                    alert('Keine Prognosedaten zum Herunterladen verfügbar');
                    return;
                }

                // Build CSV content
                let csvContent = 'Prognosedatum,Produkt-ID,Vorhergesagte Nachfrage,Konfidenzniveau\\n';
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) { // Ensure we have all 4 columns
                        const date = cells[0].textContent.trim();
                        const productId = cells[1].textContent.trim();
                        const demand = cells[2].textContent.trim();
                        const confidence = cells[3].textContent.trim();

                        // Escape any commas in the data
                        const escapedDate = date.includes(',') ? '"' + date + '"' : date;
                        const escapedProductId = productId.includes(',') ? '"' + productId + '"' : productId;
                        const escapedDemand = demand.includes(',') ? '"' + demand + '"' : demand;
                        const escapedConfidence = confidence.includes(',') ? '"' + confidence + '"' : confidence;

                        csvContent += escapedDate + ',' + escapedProductId + ',' + escapedDemand + ',' + escapedConfidence + '\\n';
                    }
                });

                // Create a Blob and download link
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'Prognosedetails_' + new Date().toISOString().slice(0, 10) + '.csv';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }

            // Function to download inventory table as CSV
            async function downloadInventoryAsCsv() {
                try {
                    // Fetch inventory data from the API
                    const response = await fetch('/api/inventory');
                    if (!response.ok) {
                        throw new Error('API responded with status ' + response.status);
                    }

                    const inventoryData = await response.json();

                    if (!Array.isArray(inventoryData) || inventoryData.length === 0) {
                        alert('Keine Inventardaten zum Herunterladen verfügbar');
                        return;
                    }

                    // Create CSV content
                    let csvContent = 'Produkt-ID,Name,Kategorie,Aktueller Bestand,Zielbestand,Letzte Warenzugang,Status' + '\\n';

                    inventoryData.forEach(item => {
                        // Determine status based on stock levels
                        let status = 'Normal';
                        if (item.current_stock < item.min_stock) {
                            status = 'Kritisch';
                        } else if (item.current_stock < item.target_stock * 0.5) {
                            status = 'Niedrig';
                        }

                        // Escape any commas in the data
                        const escapedProductId = item.product_id.includes(',') ? '"' + item.product_id + '"' : item.product_id;
                        const escapedProductName = item.product_name.includes(',') ? '"' + item.product_name + '"' : item.product_name;
                        const escapedCategory = (item.kategorie || item.category).includes(',') ? '"' + (item.kategorie || item.category) + '"' : (item.kategorie || item.category);
                        const escapedLastRestock = (item.last_restock_date || 'N/A').includes(',') ? '"' + (item.last_restock_date || 'N/A') + '"' : (item.last_restock_date || 'N/A');
                        const escapedStatus = status.includes(',') ? '"' + status + '"' : status;

                        csvContent += escapedProductId + ',' +
                                    escapedProductName + ',' +
                                    escapedCategory + ',' +
                                    item.current_stock + ',' +
                                    item.target_stock + ',' +
                                    escapedLastRestock + ',' +
                                    escapedStatus + '\\n';
                    });

                    // Create a Blob and download link
                    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = 'Lagerstatus_' + new Date().toISOString().slice(0, 10) + '.csv';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                } catch (error) {
                    console.error('Fehler beim Herunterladen des Inventars:', error);
                    alert('Fehler beim Herunterladen des Inventars: ' + error.message);
                }
            }

            // Function to handle data upload
            async function uploadData() {
                const fileInput = document.getElementById('dataFile');
                const file = fileInput.files[0];

                if (!file) {
                    alert('Bitte wählen Sie eine CSV-Datei aus');
                    return;
                }

                // Create FormData object to send the file
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const uploadDataBtn = document.getElementById('uploadDataBtn');
                    uploadDataBtn.disabled = true;
                    uploadDataBtn.textContent = 'Wird hochgeladen...';

                    const response = await fetch('/api/upload_inventory', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (response.ok) {
                        alert('Daten erfolgreich hochgeladen!');
                        // Reload the page to show updated data
                        location.reload();
                    } else {
                        alert('Fehler beim Hochladen: ' + (result.error || 'Unbekannter Fehler'));
                    }
                } catch (error) {
                    console.error('Fehler beim Hochladen:', error);
                    alert('Fehler beim Hochladen: ' + error.message);
                } finally {
                    const uploadDataBtn = document.getElementById('uploadDataBtn');
                    uploadDataBtn.disabled = false;
                    uploadDataBtn.textContent = 'Daten hochladen';
                }
            }

            // Load categories for the filter
            async function loadCategories() {
                try {
                    const response = await fetch('/api/inventory');
                    const data = await response.json();

                    if (!Array.isArray(data)) {
                        console.error('API returned non-array data:', data);
                        return;
                    }

                    // Extract unique categories (using kategorie if available, otherwise category)
                    const categories = [...new Set(data.map(item => item.kategorie || item.category))];

                    // Add categories to the main filter dropdown
                    const categorySelect = document.getElementById('categorySelect');
                    if (categorySelect) {
                        // Clear existing options except "All"
                        categorySelect.innerHTML = '<option value="all">Alle Kategorien</option>';

                        // Add an option for each category
                        categories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelect.appendChild(option);
                        });

                        // Add event listener to the dropdown
                        categorySelect.addEventListener('change', function() {
                            // Filter inventory by selected category
                            const selectedCategory = this.value;
                            loadInventoryData(selectedCategory);
                        });
                    }

                    // Add categories to the forecast dropdown as well
                    const forecastCategorySelect = document.getElementById('forecastCategorySelect');
                    if (forecastCategorySelect) {
                        // Clear existing options except "All"
                        forecastCategorySelect.innerHTML = '<option value="">Alle Kategorien</option>';

                        // Add an option for each category
                        categories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            forecastCategorySelect.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der Kategorien:', error);
                }
            }

            async function loadSapTablesReference() {
                try {
                    // Dashboard fields and their source SAP tables mapping
                    const dashboardFieldMapping = [
                        {
                            dashboardField: 'Produkt-ID',
                            sapTable: 'MARA',
                            sapField: 'MATNR',
                            description: 'Materialnummer aus Materialstammsatz'
                        },
                        {
                            dashboardField: 'Name',
                            sapTable: 'MARA',
                            sapField: 'MAKTX',
                            description: 'Material Kurztext aus Materialstammsatz'
                        },
                        {
                            dashboardField: 'Kategorie',
                            sapTable: 'MARA',
                            sapField: 'MATKL',
                            description: 'Materialgruppe aus Materialstammsatz'
                        },
                        {
                            dashboardField: 'Aktueller Bestand',
                            sapTable: 'MARD',
                            sapField: 'LABST',
                            description: 'Lagerbestand im Lagerort'
                        },
                        {
                            dashboardField: 'Zielbestand',
                            sapTable: 'MARD',
                            sapField: 'PLSTG',
                            description: 'Planbestand im Lagerort'
                        },
                        {
                            dashboardField: 'Mindestbestand',
                            sapTable: 'MARA',
                            sapField: 'BVMEH',
                            description: 'Bewirtschaftungseinheit aus Materialstammsatz'
                        },
                        {
                            dashboardField: 'Maximalbestand',
                            sapTable: 'MARA',
                            sapField: 'MAXL',
                            description: 'Maximalbestand aus Materialstammsatz'
                        },
                        {
                            dashboardField: 'Durchschn. monatl. Bedarf',
                            sapTable: 'MBEW',
                            sapField: 'AVMBM',
                            description: 'Durchschnittlicher Verbrauch/Monat aus Materialbewertung'
                        },
                        {
                            dashboardField: 'Lieferzeit in Tagen',
                            sapTable: 'MARC',
                            sapField: 'BESKZ',
                            description: 'Beschaffungsart und Lieferzeit aus Werkstammsatz'
                        },
                        {
                            dashboardField: 'Letzter Warenzugang',
                            sapTable: 'MSEG',
                            sapField: 'BUDAT',
                            description: 'Buchungsdatum Materialbewegung'
                        },
                        {
                            dashboardField: 'Historische Nachfrage',
                            sapTable: 'S091',
                            sapField: 'DATUV, WDAT, LGMNG',
                            description: 'Historische Daten für Prognose aus APO'
                        },
                        {
                            dashboardField: 'Prognose',
                            sapTable: 'S092',
                            sapField: 'PERIV, WDAT, LGMNG',
                            description: 'Prognosewerte aus APO'
                        }
                    ];

                    const tableBody = document.getElementById('sapTablesBody');
                    if (tableBody) {
                        tableBody.innerHTML = '';

                        dashboardFieldMapping.forEach(mapping => {
                            const row = document.createElement('tr');

                            row.innerHTML = '<td class="px-6 py-4 whitespace-nowrap">' + mapping.dashboardField + '</td>' + '<td class="px-6 py-4 whitespace-nowrap font-medium">' + mapping.sapTable + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + mapping.sapField + '</td>' + '<td class="px-6 py-4">' + mapping.description + '</td>';
                            tableBody.appendChild(row);
                        });
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der SAP-Tabellenreferenz:', error);
                }
            }

            async function loadInventoryData(selectedCategory = null) {
                try {
                    console.log('Lade Inventardaten...');
                    const response = await fetch('/api/inventory');
                    console.log('Antwort Status:', response.status);

                    if (!response.ok) {
                        throw new Error('API responded with status ' + response.status);
                    }

                    let data = await response.json();
                    console.log('Empfangene Inventardaten:', data);

                    // Filter data by category if a category is selected
                    if (selectedCategory && selectedCategory !== 'all') {
                        data = data.filter(item => (item.kategorie || item.category) === selectedCategory);
                    }

                    const tableBody = document.getElementById('inventoryTableBody');
                    if (tableBody) {
                        tableBody.innerHTML = '';

                        if (!Array.isArray(data) || data.length === 0) {
                            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-gray-500 py-4">Keine Inventardaten verfügbar</td></tr>';
                            return;
                        }

                        // Show all items (keeping the table scrollable via CSS max-height)
                        data.forEach(item => {
                            const row = document.createElement('tr');

                            // Determine status based on stock levels
                            let status = 'Normal';
                            let statusClass = 'bg-green-100 text-green-800';

                            if (item.current_stock < item.min_stock) {
                                status = 'Kritisch';
                                statusClass = 'bg-red-100 text-red-800';
                            } else if (item.current_stock < item.target_stock * 0.5) {
                                status = 'Niedrig';
                                statusClass = 'bg-yellow-100 text-yellow-800';
                            }

                            row.innerHTML = '<td class="px-6 py-4 whitespace-nowrap">' + item.product_id + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + item.product_name + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + (item.kategorie || item.category) + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + item.current_stock + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + item.target_stock + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + (item.last_restock_date || 'N/A') + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ' + statusClass + '">' + status + '</span>' + '</td>';
                            tableBody.appendChild(row);
                        });
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der Bestandsdaten:', error);
                    const tableBody = document.getElementById('inventoryTableBody');
                    if (tableBody) {
                        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-red-500 py-4">Fehler beim Laden der Daten: ' + error.message + '</td></tr>';
                    }
                }
            }

            async function loadDashboardStats() {
                try {
                    console.log('Lade Dashboard-Statistiken...');
                    const response = await fetch('/api/inventory/stats');
                    console.log('Statistik-Antwort Status:', response.status);

                    if (!response.ok) {
                        throw new Error('API responded with status ' + response.status);
                    }

                    const stats = await response.json();
                    console.log('Empfangene Statistiken:', stats);

                    if (stats.total_products !== undefined) {
                        const totalProductsEl = document.getElementById('totalProducts');
                        if (totalProductsEl) {
                            totalProductsEl.textContent = stats.total_products;
                        }
                    }

                    // Update At Risk Items
                    if (stats.at_risk_items) {
                        const atRiskItemsElement = document.getElementById('atRiskItems');
                        if (atRiskItemsElement) {
                            atRiskItemsElement.textContent = stats.at_risk_items.count || 0;

                            // Make the count itself also clickable
                            atRiskItemsElement.style.cursor = 'pointer';
                            atRiskItemsElement.title = 'Klicken Sie hier, um alle gefährdeten Artikel anzuzeigen';
                            atRiskItemsElement.addEventListener('click', function() {
                                window.open('/at-risk-items', '_blank');
                            });
                        }
                    }

                    // Update Low Stock Items
                    if (stats.low_stock_items) {
                        const lowStockItemsElement = document.getElementById('lowStockItems');
                        if (lowStockItemsElement) {
                            lowStockItemsElement.textContent = stats.low_stock_items.count || 0;

                            // Make the count itself also clickable
                            lowStockItemsElement.style.cursor = 'pointer';
                            lowStockItemsElement.title = 'Klicken Sie hier, um alle Artikel mit niedrigem Bestand anzuzeigen';
                            lowStockItemsElement.addEventListener('click', function() {
                                window.open('/low-stock-items', '_blank');
                            });
                        }
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der Dashboard-Statistiken:', error);
                }
            }

            async function loadDemandChart() {
                try {
                    // Initially, just show an empty chart with instructions
                    const ctx = document.getElementById('demandChart').getContext('2d');

                    // Destroy existing chart if it exists
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                    }

                    // Create an empty chart with instructions
                    window.demandChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: []
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Klicken Sie auf "Prognosen generieren" um die Nachfrageprognose anzuzeigen'
                                }
                            },
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'day',
                                        displayFormats: {
                                            day: 'dd.MM.yyyy'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Datum'
                                    }
                                },
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Nachfrage'
                                    }
                                }
                            }
                        }
                    });
                } catch (error) {
                    console.error('Fehler beim Laden des Nachfrage-Charts:', error);
                }
            }

            // Separate function to load actual demand data (called after forecasts are generated)
            async function loadActualDemandData() {
                try {
                    // Get both historical demand and forecasts
                    const [demandResponse, forecastResponse] = await Promise.all([
                        fetch('/api/historical_demand_all'),
                        fetch('/api/forecasts')
                    ]);

                    const historicalData = await demandResponse.json();
                    const forecasts = await forecastResponse.json();

                    console.log('Historische Daten empfangen:', historicalData);
                    console.log('Prognosen empfangen:', forecasts);

                    // Process data for chart
                    const ctx = document.getElementById('demandChart').getContext('2d');

                    // Destroy existing chart if it exists
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                    }

                    // Prepare datasets for the chart
                    const datasets = [];

                    // Process historical demand data
                    if (Array.isArray(historicalData) && historicalData.length > 0) {
                        // Group by product
                        const historicalByProduct = {};
                        historicalData.forEach(demand => {
                            if (!historicalByProduct[demand.product_id]) {
                                historicalByProduct[demand.product_id] = [];
                            }
                            // Only add if date and daily_demand exist
                            if (demand.date && demand.daily_demand !== undefined) {
                                historicalByProduct[demand.product_id].push({
                                    date: demand.date,
                                    demand: demand.daily_demand
                                });
                            }
                        });

                        // Add historical data as separate datasets
                        Object.entries(historicalByProduct).forEach(([productId, productData], index) => {
                            datasets.push({
                                label: productId + ' (Historisch)',
                                data: productData.map(d => ({x: d.date, y: d.demand})),
                                borderColor: 'hsl(' + (index * 70) + ', 70%, 50%)',
                                backgroundColor: 'hsla(' + (index * 70) + ', 70%, 50%, 0.1)',
                                fill: false,
                                tension: 0.1,
                                borderDash: [5, 5]  // Dashed line for historical data
                            });
                        });
                    }

                    // Process forecast data
                    if (Array.isArray(forecasts) && forecasts.length > 0) {
                        // Group forecasts by product
                        const forecastsByProduct = {};
                        forecasts.forEach(forecast => {
                            if (!forecastsByProduct[forecast.product_id]) {
                                forecastsByProduct[forecast.product_id] = [];
                            }
                            forecastsByProduct[forecast.product_id].push(forecast);
                        });

                        // Add forecast data as separate datasets
                        Object.entries(forecastsByProduct).forEach(([productId, productForecasts], index) => {
                            // Use modulo to ensure color index doesn't exceed historical index, default to 10 if no historical data
                            const historicalCount = typeof historicalByProduct !== 'undefined' && historicalByProduct ? Object.keys(historicalByProduct).length : 0;
                            const colorIndex = index % (historicalCount > 0 ? historicalCount : 10);
                            datasets.push({
                                label: productId + ' (Prognose)',
                                data: productForecasts.map(f => ({x: f.forecast_date, y: f.predicted_demand})),
                                borderColor: 'hsl(' + (colorIndex * 70 + 30) + ', 70%, 50%)',
                                backgroundColor: 'hsla(' + (colorIndex * 70 + 30) + ', 70%, 50%, 0.1)',
                                fill: false,
                                tension: 0.1
                            });
                        });
                    }

                    console.log('Datasets vorbereitet:', datasets);

                    window.demandChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'day',
                                        displayFormats: {
                                            day: 'dd.MM.yyyy'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Datum'
                                    }
                                },
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Nachfrage'
                                    }
                                }
                            }
                        }
                    });
                } catch (error) {
                    console.error('Fehler beim Laden des Nachfrage-Charts:', error);
                }
            }

            async function loadForecastTable() {
                try {
                    const response = await fetch('/api/forecasts');
                    const forecasts = await response.json();

                    const tableBody = document.getElementById('forecastTableBody');
                    if (tableBody) {
                        tableBody.innerHTML = '';

                        if (forecasts.length === 0) {
                            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-gray-500 py-4">Keine Prognosedaten verfügbar. Erstelle Prognosen zuerst.</td></tr>';
                            return;
                        }

                        // Sort forecasts by date to match the demand graph order
                        forecasts.sort((a, b) => new Date(a.forecast_date) - new Date(b.forecast_date));

                        forecasts.forEach(forecast => {
                            const row = document.createElement('tr');

                            row.innerHTML = '<td class="px-6 py-4 whitespace-nowrap">' + forecast.forecast_date + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + forecast.product_id + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + (forecast.predicted_demand ? forecast.predicted_demand.toFixed(2) : 'N/A') + '</td>' + '<td class="px-6 py-4 whitespace-nowrap">' + (forecast.confidence_level ? (forecast.confidence_level * 100).toFixed(1) + '%' : 'N/A') + '</td>';
                            tableBody.appendChild(row);
                        });
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der Prognosetabelle:', error);
                }
            }

            async function generateForecast() {
                const forecastBtn = document.getElementById('forecastBtn');
                const startDateInput = document.getElementById('startDate');
                const endDateInput = document.getElementById('endDate');
                const durationSelect = document.getElementById('forecastDuration');
                const forecastCategorySelect = document.getElementById('forecastCategorySelect');

                if (forecastBtn) {
                    forecastBtn.disabled = true;
                    forecastBtn.textContent = 'Wird generiert...';
                }

                try {
                    // Get selected dates and duration
                    const startDate = startDateInput ? startDateInput.value || new Date().toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
                    const endDate = endDateInput ? endDateInput.value ||
                                   new Date(new Date().setDate(new Date().getDate() + parseInt(durationSelect ? durationSelect.value : 7))).toISOString().split('T')[0] :
                                   new Date(new Date().setDate(new Date().getDate() + 7)).toISOString().split('T')[0];

                    // Calculate duration in days
                    const start = new Date(startDate);
                    const end = new Date(endDate);
                    const duration = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1; // Include both start and end dates

                    // Get selected category
                    const selectedCategory = forecastCategorySelect ? forecastCategorySelect.value : '';

                    const response = await fetch('/api/generate_forecasts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            start_date: startDate,
                            end_date: endDate,
                            forecast_duration: duration,
                            category: selectedCategory  // Add selected category
                        })
                    });

                    const result = await response.json();

                    const forecastResult = document.getElementById('forecastResult');
                    if (forecastResult) {
                        forecastResult.innerHTML = '<div class="p-4 bg-green-50 text-green-800 rounded">' + result.message + '</div>';
                    }

                    // Reload data after generating forecasts
                    loadInventoryData();
                    loadDashboardStats();
                    loadActualDemandData();  // Load the actual demand data with forecasts
                    loadForecastTable();
                } catch (error) {
                    console.error('Fehler beim Generieren der Prognose:', error);
                    const forecastResult = document.getElementById('forecastResult');
                    if (forecastResult) {
                        forecastResult.innerHTML = '<div class="p-4 bg-red-50 text-red-800 rounded">Fehler beim Generieren der Prognosen: ' + error.message + '</div>';
                    }
                } finally {
                    if (forecastBtn) {
                        forecastBtn.disabled = false;
                        forecastBtn.textContent = 'Prognosen generieren';
                    }
                }
            }

            async function interpretResults() {
                const interpretBtn = document.getElementById('interpretBtn');
                const interpretResult = document.getElementById('interpretResult');
                const interpretationContent = document.getElementById('interpretationContent');

                if (interpretBtn) {
                    interpretBtn.disabled = true;
                    interpretBtn.textContent = 'Interpretiere mit KI...';
                }

                // Clear the text and show progress bar
                if (interpretationContent) {
                    interpretationContent.innerHTML = '<div class="flex items-center"><div class="w-full bg-gray-200 rounded-full h-2.5 mr-2"><div class="bg-blue-600 h-2.5 rounded-full animate-pulse" id="progressBar" style="width: 60%"></div></div><span>Verarbeite...</span></div>';
                }

                if (interpretResult) {
                    interpretResult.classList.remove('hidden');
                }

                try {
                    // Get selected products from the category product container
                    const container = document.getElementById('categoryProductContainer');
                    let selectedProducts = [];

                    if (container) {
                        // Get checked product checkboxes
                        const productCheckboxes = container.querySelectorAll('.product-checkbox');
                        selectedProducts = Array.from(productCheckboxes)
                            .filter(checkbox => checkbox.checked)
                            .map(checkbox => checkbox.value);
                    }

                    // Send the selected products to the backend
                    const response = await fetch('/api/interpret_results', {
                        method: 'POST',  // Changed to POST to send selected products
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            selected_products: selectedProducts
                        })
                    });

                    const result = await response.json();

                    if (result.status === 'success') {
                        if (interpretationContent) {
                            interpretationContent.innerHTML = result.interpretation.replace(/\\n/g, '<br>');
                        }
                    } else {
                        if (interpretationContent) {
                            interpretationContent.innerHTML = 'Fehler: ' + result.error;
                        }
                    }
                } catch (error) {
                    console.error('Fehler bei der KI-Interpretation:', error);
                    if (interpretationContent) {
                        interpretationContent.innerHTML = 'Fehler bei der KI-Interpretation: ' + error.message;
                    }
                } finally {
                    if (interpretBtn) {
                        interpretBtn.disabled = false;
                        interpretBtn.textContent = 'Ergebnisse mit KI interpretieren';
                    }
                }
            }

            // Load products and create a category-based hierarchical selection
            async function loadProductsForDropdown() {
                try {
                    const response = await fetch('/api/inventory');
                    const data = await response.json();

                    if (!Array.isArray(data)) {
                        console.error('API returned non-array data:', data);
                        return;
                    }

                    const container = document.getElementById('categoryProductContainer');
                    if (container) {
                        // Clear existing content
                        container.innerHTML = '';

                        // Group products by category
                        const productsByCategory = {};
                        data.forEach(item => {
                            const category = item.kategorie || item.category || 'Sonstige';
                            if (!productsByCategory[category]) {
                                productsByCategory[category] = [];
                            }
                            productsByCategory[category].push(item);
                        });

                        // Create container for each category
                        Object.entries(productsByCategory).forEach(([category, products]) => {
                            // Create category header
                            const categoryDiv = document.createElement('div');
                            categoryDiv.className = 'mb-3 border-b pb-2';

                            const categoryHeader = document.createElement('div');
                            categoryHeader.className = 'flex items-center cursor-pointer py-1';
                            categoryHeader.innerHTML = '<span class="mr-2 text-lg">▶</span>' + '<input type="checkbox" id="cat_' + category + '" class="mr-2 category-checkbox">' + '<label for="cat_' + category + '" class="font-medium text-sm">' + category + '</label>' + '<span class="ml-auto text-xs text-gray-500">(' + products.length + ' Produkte)</span>';

                            const productList = document.createElement('div');
                            productList.className = 'ml-6 mt-2 hidden';  // Initially hidden
                            productList.id = 'products_' + category;

                            // Add products to this category
                            products.forEach(item => {
                                const productDiv = document.createElement('div');
                                productDiv.className = 'flex items-center mb-1 ml-4';
                                productDiv.innerHTML = '<input type="checkbox" id="product_' + item.product_id + '" value="' + item.product_id + '" class="mr-2 product-checkbox" data-category="' + category + '">' + '<label for="product_' + item.product_id + '" class="text-sm">' + item.product_id + ' - ' + item.product_name + '</label>';
                                productList.appendChild(productDiv);
                            });

                            categoryDiv.appendChild(categoryHeader);
                            categoryDiv.appendChild(productList);
                            container.appendChild(categoryDiv);

                            // Add event listener to toggle visibility of products in this category
                            categoryHeader.addEventListener('click', function(e) {
                                // Don't toggle if checkbox or label was clicked directly
                                if (e.target.tagName === 'INPUT' || e.target.tagName === 'LABEL') {
                                    return;
                                }

                                const arrow = this.querySelector('span');
                                const productsDiv = document.getElementById('products_' + category);
                                if (productsDiv.classList.contains('hidden')) {
                                    productsDiv.classList.remove('hidden');
                                    arrow.textContent = '▼';  // Down arrow when expanded
                                } else {
                                    productsDiv.classList.add('hidden');
                                    arrow.textContent = '▶';  // Right arrow when collapsed
                                }
                            });

                            // Add event listener to category checkbox to select/deselect all products in category
                            const categoryCheckbox = document.getElementById('cat_' + category);
                            categoryCheckbox.addEventListener('change', function() {
                                const productCheckboxes = productList.querySelectorAll('input[type="checkbox"]');
                                productCheckboxes.forEach(checkbox => {
                                    checkbox.checked = this.checked;
                                });
                                updateCategoryCheckboxes();
                                loadActualDemandData();
                            });

                            // Add event listeners to individual product checkboxes
                            const productCheckboxes = productList.querySelectorAll('input[type="checkbox"]');
                            productCheckboxes.forEach(checkbox => {
                                checkbox.addEventListener('change', function() {
                                    updateCategoryCheckboxes();
                                    loadActualDemandData();
                                });
                            });
                        });
                    }
                } catch (error) {
                    console.error('Fehler beim Laden der Produkte für die Auswahl:', error);
                }
            }

            // Helper function to update category checkboxes based on product selections
            function updateCategoryCheckboxes() {
                const container = document.getElementById('categoryProductContainer');
                if (container) {
                    // Get all categories
                    const categoryCheckboxes = container.querySelectorAll('.category-checkbox');
                    categoryCheckboxes.forEach(catCheckbox => {
                        const categoryId = catCheckbox.id.replace('cat_', '');
                        const productCheckboxes = container.querySelectorAll('.product-checkbox[data-category="' + categoryId + '"]');

                        if (productCheckboxes.length === 0) return;

                        const checkedProducts = Array.from(productCheckboxes).filter(cb => cb.checked);
                        catCheckbox.checked = checkedProducts.length === productCheckboxes.length;
                        catCheckbox.indeterminate = checkedProducts.length > 0 && checkedProducts.length < productCheckboxes.length;
                    });
                }
            }

            // Modified function to load forecast data based on selected products (category-based selection)
            // This function now loads only forecast data for the selected products
            async function loadActualDemandData() {
                const container = document.getElementById('categoryProductContainer');
                let selectedProducts = [];

                if (container) {
                    // Get checked product checkboxes
                    const productCheckboxes = container.querySelectorAll('.product-checkbox');
                    selectedProducts = Array.from(productCheckboxes)
                        .filter(checkbox => checkbox.checked)
                        .map(checkbox => checkbox.value);
                }

                try {
                    // Initialize datasets array to hold forecast data
                    const datasets = [];

                    if (selectedProducts.length > 0) {
                        // Fetch forecast data for selected products
                        try {
                            // Fetch all forecasts
                            const forecastResponse = await fetch('/api/forecasts');
                            const allForecasts = await forecastResponse.json();

                            // Filter forecasts for selected products only
                            const filteredForecasts = allForecasts.filter(f => selectedProducts.includes(f.product_id));

                            // Group forecast data by product
                            const forecastsByProduct = {};
                            filteredForecasts.forEach(forecast => {
                                if (!forecastsByProduct[forecast.product_id]) {
                                    forecastsByProduct[forecast.product_id] = [];
                                }
                                forecastsByProduct[forecast.product_id].push(forecast);
                            });

                            // Add forecast data as separate datasets
                            Object.entries(forecastsByProduct).forEach(([productId, productForecasts], index) => {
                                datasets.push({
                                    label: productId + ' (Prognose)',
                                    data: productForecasts.map(f => ({x: f.forecast_date, y: f.predicted_demand})),
                                    borderColor: 'hsl(' + (index * 70) + ', 70%, 50%)',
                                    backgroundColor: 'hsla(' + (index * 70) + ', 70%, 50%, 0.1)',
                                    fill: false,
                                    tension: 0.1
                                });
                            });
                        } catch (apiError) {
                            console.error('API request failed:', apiError);
                        }
                    } else {
                        // When no products are selected, show a message
                        console.log('No products selected, showing message chart');
                    }

                    console.log('Datasets vorbereitet:', datasets);

                    // Process data for chart
                    const ctx = document.getElementById('demandChart').getContext('2d');

                    // Destroy existing chart if it exists
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                    }

                    // If no data at all, create an empty chart with a message
                    if (datasets.length === 0) {
                        window.demandChart = new Chart(ctx, {
                            type: 'line',
                            data: {
                                datasets: []
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    title: {
                                        display: true,
                                        text: selectedProducts.length > 0 ?
                                            'Keine Prognosedaten für die ausgewählten Produkte verfügbar' :
                                            'Wählen Sie Produkte aus und generieren Sie Prognosen, um die Nachfrage anzuzeigen.'
                                    }
                                },
                                scales: {
                                    x: {
                                        type: 'time',
                                        time: {
                                            unit: 'day',
                                            displayFormats: {
                                                day: 'dd.MM.yyyy'
                                            }
                                        },
                                        title: {
                                            display: true,
                                            text: 'Datum'
                                        }
                                    },
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Nachfrage'
                                        }
                                    }
                                }
                            }
                        });
                        return;
                    }

                    window.demandChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'day',
                                        displayFormats: {
                                            day: 'dd.MM.yyyy'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Datum'
                                    }
                                },
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Nachfrage'
                                    }
                                }
                            }
                        }
                    });
                } catch (error) {
                    console.error('Fehler beim Laden des Nachfrage-Charts:', error);

                    // Show error in chart
                    const ctx = document.getElementById('demandChart').getContext('2d');
                    if (window.demandChart && typeof window.demandChart.destroy === 'function') {
                        window.demandChart.destroy();
                    }

                    window.demandChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: []
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Fehler beim Laden der Daten: ' + error.message
                                }
                            }
                        }
                    });
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Get all inventory items."""
    try:
        conn = get_db_connection()
        inventory = conn.execute('SELECT * FROM inventory ORDER BY product_id').fetchall()
        conn.close()
        
        inventory_list = [dict(row) for row in inventory]
        print(f"DEBUG: Returning {len(inventory_list)} inventory items")
        return jsonify(inventory_list)
    except Exception as e:
        print(f"ERROR in get_inventory: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<product_id>', methods=['GET'])
def get_inventory_item(product_id):
    """Get specific inventory item."""
    try:
        conn = get_db_connection()
        item = conn.execute('SELECT * FROM inventory WHERE product_id = ?', (product_id,)).fetchone()
        conn.close()

        if item:
            return jsonify(dict(item))
        else:
            return jsonify({'error': 'Artikel nicht gefunden'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<product_id>', methods=['PUT'])
def update_inventory_item(product_id):
    """Update inventory item."""
    try:
        data = request.json
        conn = get_db_connection()

        conn.execute('''
            UPDATE inventory
            SET current_stock = ?, target_stock = ?, min_stock = ?, max_stock = ?, avg_monthly_demand = ?
            WHERE product_id = ?
        ''', (
            data['current_stock'],
            data['target_stock'],
            data['min_stock'],
            data['max_stock'],
            data['avg_monthly_demand'],
            product_id
        ))
        conn.commit()

        # Return updated item
        item = conn.execute('SELECT * FROM inventory WHERE product_id = ?', (product_id,)).fetchone()
        conn.close()

        return jsonify(dict(item))
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/stats', methods=['GET'])
def get_inventory_stats():
    """Get inventory statistics."""
    try:
        conn = get_db_connection()

        # Count total products
        total_products = conn.execute('SELECT COUNT(*) FROM inventory').fetchone()[0]

        # Get items at risk (current stock below min)
        at_risk_items = conn.execute(
            'SELECT product_id, product_name FROM inventory WHERE current_stock < min_stock'
        ).fetchall()
        at_risk_items_count = len(at_risk_items)

        # Get items with low stock (below 50% of target)
        low_stock_items = conn.execute(
            'SELECT product_id, product_name FROM inventory WHERE current_stock < (target_stock * 0.5) AND current_stock >= min_stock'
        ).fetchall()
        low_stock_items_count = len(low_stock_items)

        conn.close()

        return jsonify({
            'total_products': total_products,
            'at_risk_items': {
                'count': at_risk_items_count,
                'items': [dict(row) for row in at_risk_items],
                'url': '/at-risk-items'  # Add a URL to view all at-risk items
            },
            'low_stock_items': {
                'count': low_stock_items_count,
                'items': [dict(row) for row in low_stock_items],
                'url': '/low-stock-items'  # Add a URL to view all low stock items
            }
        })
    except Exception as e:
        print(f"ERROR in get_inventory_stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/at-risk-items')
def at_risk_items_page():
    """Page to display all items at risk (current stock below min)."""
    html_content = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gefährdete Artikel</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-gray-800">Gefährdete Artikel</h1>
                <a href="/" class="text-blue-600 hover:text-blue-800 font-medium">← Zurück zum Dashboard</a>
            </div>

            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produkt-ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kategorie</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aktueller Bestand</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mindestbestand</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody id="atRiskTableBody" class="bg-white divide-y divide-gray-200">
                            <tr>
                                <td colspan="6" class="text-center py-4">Lade Daten...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            async function loadAtRiskItems() {
                try {
                    const response = await fetch('/api/inventory');
                    const allItems = await response.json();

                    // Filter for items where current stock is below minimum
                    const atRiskItems = allItems.filter(item => item.current_stock < item.min_stock);

                    const tableBody = document.getElementById('atRiskTableBody');
                    tableBody.innerHTML = '';

                    if (atRiskItems.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">Keine gefährdeten Artikel vorhanden</td></tr>';
                        return;
                    }

                    atRiskItems.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">${item.product_id}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.product_name}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.kategorie || item.category}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.current_stock}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.min_stock}</td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                                    Gefährdet
                                </span>
                            </td>
                        `;
                        tableBody.appendChild(row);
                    });
                } catch (error) {
                    console.error('Fehler beim Laden der gefährdeten Artikel:', error);
                    const tableBody = document.getElementById('atRiskTableBody');
                    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-red-500">Fehler beim Laden der Daten: ' + error.message + '</td></tr>';
                }
            }

            document.addEventListener('DOMContentLoaded', loadAtRiskItems);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)


@app.route('/low-stock-items')
def low_stock_items_page():
    """Page to display all items with low stock (below 50% of target)."""
    html_content = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artikel mit niedrigem Bestand</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-gray-800">Artikel mit niedrigem Bestand</h1>
                <a href="/" class="text-blue-600 hover:text-blue-800 font-medium">← Zurück zum Dashboard</a>
            </div>

            <div class="bg-white p-6 rounded-lg shadow-md">
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produkt-ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kategorie</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aktueller Bestand</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Zielbestand</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody id="lowStockTableBody" class="bg-white divide-y divide-gray-200">
                            <tr>
                                <td colspan="6" class="text-center py-4">Lade Daten...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            async function loadLowStockItems() {
                try {
                    const response = await fetch('/api/inventory');
                    const allItems = await response.json();

                    // Filter for items where current stock is below 50% of target but above minimum
                    const lowStockItems = allItems.filter(item =>
                        item.current_stock < (item.target_stock * 0.5) &&
                        item.current_stock >= item.min_stock
                    );

                    const tableBody = document.getElementById('lowStockTableBody');
                    tableBody.innerHTML = '';

                    if (lowStockItems.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">Keine Artikel mit niedrigem Bestand vorhanden</td></tr>';
                        return;
                    }

                    lowStockItems.forEach(item => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap">${item.product_id}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.product_name}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.kategorie || item.category}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.current_stock}</td>
                            <td class="px-6 py-4 whitespace-nowrap">${item.target_stock}</td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                                    Niedrig
                                </span>
                            </td>
                        `;
                        tableBody.appendChild(row);
                    });
                } catch (error) {
                    console.error('Fehler beim Laden der Artikel mit niedrigem Bestand:', error);
                    const tableBody = document.getElementById('lowStockTableBody');
                    tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-red-500">Fehler beim Laden der Daten: ' + error.message + '</td></tr>';
                }
            }

            document.addEventListener('DOMContentLoaded', loadLowStockItems);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route('/api/demand/<product_id>', methods=['GET'])
def get_historical_demand(product_id):
    """Get historical demand for a specific product."""
    try:
        conn = get_db_connection()
        demand = conn.execute(
            'SELECT date, daily_demand FROM historical_demand WHERE product_id = ? ORDER BY date',
            (product_id,)
        ).fetchall()
        conn.close()

        return jsonify([dict(row) for row in demand])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical_demand_all', methods=['GET'])
def get_all_historical_demand():
    """Get historical demand for all products."""
    try:
        conn = get_db_connection()
        demand = conn.execute(
            'SELECT date, product_id, daily_demand FROM historical_demand ORDER BY date'
        ).fetchall()
        conn.close()

        return jsonify([dict(row) for row in demand])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecasts', methods=['GET'])
def get_all_forecasts():
    """Get all forecasts."""
    try:
        conn = get_db_connection()
        forecasts = conn.execute('''
            SELECT product_id, forecast_date, predicted_demand, confidence_level, created_at
            FROM forecasts
            ORDER BY forecast_date
        ''').fetchall()
        conn.close()

        return jsonify([dict(row) for row in forecasts])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecasts/<product_id>', methods=['GET'])
def get_forecasts_for_product(product_id):
    """Get forecasts for a specific product."""
    try:
        conn = get_db_connection()
        forecasts = conn.execute(
            'SELECT forecast_date, predicted_demand, confidence_level FROM forecasts WHERE product_id = ? ORDER BY forecast_date',
            (product_id,)
        ).fetchall()
        conn.close()

        return jsonify([dict(row) for row in forecasts])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def call_sap_rpt1_for_forecasting(product_id, historical_data, forecast_horizon=7):
    """
    Mock function to simulate calling SAP RPT-1 for demand forecasting.
    In a real implementation, this would make an API call to SAP RPT-1 service.
    """
    try:
        # Simulate SAP RPT-1 processing time
        import time
        time.sleep(0.1)

        # For demonstration purposes, we'll use a simple statistical model
        # In reality, SAP RPT-1 would process the tabular data and return more accurate predictions
        if len(historical_data) == 0:
            # If no historical data, use the average from inventory
            avg_daily_demand = 5  # Default value
        else:
            # Calculate average demand from historical data
            avg_daily_demand = historical_data['daily_demand'].mean()

        # Generate forecasts using a more sophisticated approach
        forecasts = []
        for i in range(1, forecast_horizon + 1):
            forecast_date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')

            # Apply trend and seasonality if available
            # This is a simplified model - SAP RPT-1 would handle complex patterns
            trend_factor = 1 + (i * 0.01)  # Slight increasing trend
            predicted_demand = avg_daily_demand * trend_factor

            # Add some random variation to simulate real world uncertainty
            predicted_demand = np.random.normal(predicted_demand, predicted_demand * 0.1)

            # Ensure non-negative demand
            predicted_demand = max(0, predicted_demand)

            forecasts.append({
                'forecast_date': forecast_date,
                'predicted_demand': predicted_demand
            })

        return forecasts

    except Exception as e:
        # In a real implementation, log the error and possibly fall back to a simpler model
        print(f"Fehler in SAP RPT-1 Prognose-Simulation: {str(e)}")
        # Return default forecast
        forecasts = []
        for i in range(1, forecast_horizon + 1):
            forecast_date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            forecasts.append({
                'forecast_date': forecast_date,
                'predicted_demand': 5  # Default value
            })
        return forecasts


@app.route('/api/generate_forecasts', methods=['POST'])
def generate_forecasts():
    """Generate demand forecasts for all products using SAP RPT-1."""
    try:
        conn = get_db_connection()

        # Get request data
        request_data = request.json
        start_date = request_data.get('start_date', datetime.now().strftime('%Y-%m-%d'))
        end_date = request_data.get('end_date', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        forecast_duration = request_data.get('forecast_duration', 7)
        selected_category = request_data.get('category', '')  # Get selected category

        # Parse the start and end dates to calculate the number of days
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        actual_duration = (end_dt - start_dt).days + 1  # Include both start and end dates

        # Clear existing forecasts (keep only forecasts for dates in the past)
        cutoff_date = datetime.now().strftime('%Y-%m-%d')
        conn.execute('DELETE FROM forecasts WHERE forecast_date >= ?', (cutoff_date,))

        # Get products - limit to selected category if specified
        if selected_category:
            products = conn.execute('''
                SELECT product_id FROM inventory
                WHERE kategorie = ? OR category = ?
            ''', (selected_category, selected_category)).fetchall()
        else:
            products = conn.execute('SELECT product_id FROM inventory').fetchall()

        # Process each product to generate forecasts
        for product in products:
            product_id = product['product_id']

            # Get historical demand data for this specific product
            historical_data = conn.execute('''
                SELECT date, daily_demand, price, marketing_spend, seasonal_factor
                FROM historical_demand
                WHERE product_id = ?
                ORDER BY date
            ''', (product_id,)).fetchall()

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(historical_data, columns=['date', 'daily_demand', 'price', 'marketing_spend', 'seasonal_factor'])

            # Call SAP RPT-1 for forecasting (simulated) with the specified duration
            forecasts = call_sap_rpt1_for_forecasting(product_id, df, actual_duration)

            # Insert forecasts into the database
            for forecast in forecasts:
                # Calculate days from today for this forecast
                forecast_date = datetime.strptime(forecast['forecast_date'], '%Y-%m-%d')
                days_from_today = (forecast_date - datetime.now()).days

                # Base confidence decreases with time (e.g., from 95% at day 1 to 85% at day 7)
                base_confidence = max(0.85, 0.95 - (days_from_today * 0.015))

                # Add some randomness to make it more realistic
                confidence_level = base_confidence - (np.random.random() * 0.02)  # Up to 2% variation
                confidence_level = max(0.80, min(0.98, confidence_level))  # Keep between 80% and 98%

                conn.execute('''
                    INSERT INTO forecasts (product_id, forecast_date, predicted_demand, confidence_level)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, forecast['forecast_date'], forecast['predicted_demand'], confidence_level))

        conn.commit()
        conn.close()

        # Update the success message to include category info if specified
        category_info = f' für Kategorie "{selected_category}"' if selected_category else ' für alle Kategorien'
        return jsonify({'message': f'Prognosen erfolgreich mit SAP RPT-1 Simulation generiert{category_info} für {actual_duration} Tage ({start_date} bis {end_date})'})
    except Exception as e:
        print(f"ERROR in generate_forecasts: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimize_inventory', methods=['POST'])
def optimize_inventory():
    """Optimize inventory based on forecasts."""
    try:
        conn = get_db_connection()

        # Get forecasts for the next week
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        forecasts = conn.execute('''
            SELECT product_id, SUM(predicted_demand) as total_predicted_demand
            FROM forecasts
            WHERE forecast_date <= ?
            GROUP BY product_id
        ''', (next_week,)).fetchall()

        # Update inventory levels based on forecasts
        for forecast in forecasts:
            product_id = forecast['product_id']
            total_predicted_demand = forecast['total_predicted_demand']

            # Get current inventory
            inventory_item = conn.execute(
                'SELECT current_stock, lead_time_days, min_stock, target_stock FROM inventory WHERE product_id = ?',
                (product_id,)
            ).fetchone()

            if inventory_item:
                current_stock = inventory_item['current_stock']
                lead_time_days = inventory_item['lead_time_days']
                min_stock = inventory_item['min_stock']
                target_stock = inventory_item['target_stock']

                # Calculate reorder point: demand during lead time + safety stock
                avg_daily_demand = total_predicted_demand / 7  # Average daily demand for next week
                demand_during_lead_time = avg_daily_demand * lead_time_days
                safety_stock = avg_daily_demand * 3  # 3 days of safety stock

                reorder_point = demand_during_lead_time + safety_stock

                # Calculate recommended order quantity
                if current_stock < reorder_point:
                    recommended_order = max(target_stock, reorder_point * 1.5) - current_stock
                    recommended_order = round(recommended_order)
                else:
                    recommended_order = 0

                # Update recommendation in inventory
                conn.execute('''
                    UPDATE inventory
                    SET target_stock = ?
                    WHERE product_id = ?
                ''', (max(target_stock, current_stock + recommended_order), product_id))

        conn.commit()
        conn.close()

        return jsonify({'message': 'Inventaroptimierung abgeschlossen'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/interpret_results', methods=['POST'])  # Changed to POST to accept selected products
def interpret_results():
    """Use Ollama to interpret inventory results in German for selected products."""
    try:
        # Get selected products from request
        request_data = request.json
        selected_products = request_data.get('selected_products', []) if request_data else []

        # Get current inventory and forecast data
        conn = get_db_connection()

        if selected_products:
            # Filter data for selected products only
            placeholders = ','.join(['?' for _ in selected_products])

            # Get inventory data for selected products
            inventory_query = f"SELECT * FROM inventory WHERE product_id IN ({placeholders})"
            inventory = conn.execute(inventory_query, selected_products).fetchall()
            inventory_data = [dict(row) for row in inventory]

            # Get forecast data for selected products
            forecast_query = f"SELECT product_id, forecast_date, predicted_demand, confidence_level FROM forecasts WHERE product_id IN ({placeholders}) ORDER BY forecast_date"
            forecasts = conn.execute(forecast_query, selected_products).fetchall()
            forecast_data = [dict(row) for row in forecasts]

            # Get statistics for selected products
            if selected_products:
                stats_query = f"""
                    SELECT
                        COUNT(*) as total_products,
                        SUM(CASE WHEN current_stock < min_stock THEN 1 ELSE 0 END) as at_risk_items,
                        SUM(CASE WHEN current_stock < (target_stock * 0.5) AND current_stock >= min_stock THEN 1 ELSE 0 END) as low_stock_items
                    FROM inventory
                    WHERE product_id IN ({placeholders})
                """
                stats = conn.execute(stats_query, selected_products).fetchone()
            else:
                # If no products selected, return zero stats
                stats = {'total_products': 0, 'at_risk_items': 0, 'low_stock_items': 0}
        else:
            # Get all data if no products selected
            inventory = conn.execute('SELECT * FROM inventory').fetchall()
            inventory_data = [dict(row) for row in inventory]

            forecasts = conn.execute('''
                SELECT product_id, forecast_date, predicted_demand, confidence_level
                FROM forecasts
                ORDER BY forecast_date
            ''').fetchall()
            forecast_data = [dict(row) for row in forecasts]

            # Get statistics
            stats = conn.execute('''
                SELECT
                    COUNT(*) as total_products,
                    SUM(CASE WHEN current_stock < min_stock THEN 1 ELSE 0 END) as at_risk_items,
                    SUM(CASE WHEN current_stock < (target_stock * 0.5) AND current_stock >= min_stock THEN 1 ELSE 0 END) as low_stock_items
                FROM inventory
            ''').fetchone()

        conn.close()

        # Prepare data for the LLM
        data_summary = f"""
        Inventar-Statistiken für ausgewählte Produkte:
        - Gesamtprodukte: {stats['total_products']}
        - Gefährdete Artikel (unter Mindestbestand): {stats['at_risk_items']}
        - Artikel mit niedrigem Bestand: {stats['low_stock_items']}

        Beispiel-Inventardaten:
        {str(inventory_data[:2])}  # Nur die ersten 2 Artikel zur Veranschaulichung

        Beispiel-Prognosedaten:
        {str(forecast_data[:5])}  # Nur die ersten 5 Prognosen zur Veranschaulichung

        Bitte interpretiere diese Lager- und Nachfrageprognosedaten für die ausgewählten Produkte auf Deutsch in klaren Sätzen.
        Erkläre den aktuellen Status, potenzielle Probleme und gebe Empfehlungen für die Lagerverwaltung.
        """

        # Call Ollama to get interpretation in German using the specific model requested
        try:
            response = ollama.chat(
                model='gpt-oss:20b-cloud',  # Using the specific model requested
                messages=[
                    {
                        'role': 'user',
                        'content': f"Bitte interpretiere diese Lager- und Nachfrageprognosedaten für die ausgewählten Produkte auf Deutsch in klaren, einfachen Sätzen. Daten: {data_summary}"
                    }
                ]
            )
        except Exception as model_error:
            # If the specific model fails (e.g., due to authentication), try to use a local model
            print(f"Specific model failed: {str(model_error)}, trying local model")
            try:
                # Get list of available models
                models_response = ollama.list()
                available_models = [model['name'].split(':')[0] for model in models_response['models']]  # Get model names without tags

                # Try to use a local model if available
                local_model = None
                for model_name in ['llama3', 'mistral', 'gemma', 'phi']:
                    if model_name in available_models:
                        local_model = model_name
                        break

                if local_model:
                    response = ollama.chat(
                        model=local_model,
                        messages=[
                            {
                                'role': 'user',
                                'content': f"Bitte interpretiere diese Lager- und Nachfrageprognosedaten für die ausgewählten Produkte auf Deutsch in klaren, einfachen Sätzen. Daten: {data_summary}"
                            }
                        ]
                    )
                else:
                    raise Exception(f"Kein verfügbares Ollama-Modell gefunden: {str(model_error)}")
            except Exception as fallback_error:
                raise Exception(f"Ollama Interpretation fehlgeschlagen: {str(model_error)}. Fallback failed: {str(fallback_error)}")

        interpretation = response['message']['content']

        return jsonify({
            'interpretation': interpretation,
            'status': 'success'
        })

    except Exception as e:
        return jsonify({
            'error': f'Fehler bei der Interpretation durch Ollama: {str(e)}',
            'status': 'error'
        }), 500


@app.route('/api/clear_forecasts', methods=['POST'])
def clear_forecasts():
    """Clear all forecast data from the database."""
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM forecasts")
        conn.commit()
        conn.close()
        return jsonify({'message': 'Alle Prognosedaten wurden gelöscht'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload_inventory', methods=['POST'])
def upload_inventory():
    """Upload inventory data from a CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Nur CSV-Dateien sind erlaubt'}), 400

        # Read the CSV file
        import io
        import csv

        # Read content from uploaded file
        content = file.read().decode('utf-8')
        csv_data = io.StringIO(content)
        reader = csv.DictReader(csv_data)

        # Validate required columns
        required_columns = [
            'product_id', 'product_name', 'category', 'current_stock', 'target_stock',
            'min_stock', 'max_stock', 'avg_monthly_demand', 'lead_time_days', 'last_restock_date'
        ]

        # Check if all required columns exist
        for col in required_columns:
            if col not in reader.fieldnames:
                return jsonify({'error': f'Fehlende Spalte: {col}'}), 400

        # Create a backup of the current database before clearing
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"sap_inventory_{timestamp}.db"
        shutil.copy(DATABASE, backup_filename)

        # Connect to database and clear existing inventory
        conn = get_db_connection()

        # Clear existing inventory data
        conn.execute("DELETE FROM inventory")

        # Insert new data
        for row in reader:
            conn.execute('''
                INSERT INTO inventory (
                    product_id, product_name, category, current_stock, target_stock,
                    min_stock, max_stock, avg_monthly_demand, lead_time_days, last_restock_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['product_id'],
                row['product_name'],
                row['category'],
                int(row['current_stock']),
                int(row['target_stock']),
                int(row['min_stock']),
                int(row['max_stock']),
                float(row['avg_monthly_demand']),
                int(row['lead_time_days']),
                row.get('last_restock_date', None)  # Use get to allow None if missing
            ))

        conn.commit()
        conn.close()

        return jsonify({'message': f'Daten erfolgreich aus {file.filename} hochgeladen und importiert'})

    except Exception as e:
        print(f"ERROR in upload_inventory: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Fehler beim Verarbeiten der Datei: {str(e)}'}), 500

if __name__ == '__main__':
    print("Initialisiere Datenbank...")
    init_db()
    print("Starte Flask-Anwendung auf http://0.0.0.0:5020")
    app.run(debug=True, host='0.0.0.0', port=5020)