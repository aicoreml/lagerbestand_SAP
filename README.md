# SAP Lagerbestandsprognose System

This project is a web-based application for managing inventory levels with SAP-like data and functions, simulating the functionality of SAP ERP modules for warehouse management with forecasting capabilities.

## Features

- Real-time inventory dashboard
- Category filtering with dropdown
- Forecasting functions for future inventory
- AI-powered analysis with Ollama
- SAP-ERP table reference
- CSV import functionality
- SAP-like data structure with 300 entries generated using Faker
- **NEW**: Clickable dashboard elements for "Gefährdete Artikel" and "Artikel mit niedrigem Bestand" that open detailed views in new tabs
- **NEW**: Forecast-only chart that responds to product selections in the category dropdown
- **NEW**: Direct data path fixing to ensure consistent database access

## Installation and Setup

### Prerequisites

- Python 3.8+
- Ollama (for AI analysis)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd lagerbestand_SAP
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install and start Ollama:
   - Follow installation instructions at https://ollama.ai/
   - Pull a model for AI analysis:
     ```bash
     ollama pull llama3
     # or another supported model
     ```

5. Generate sample data:
   ```bash
   python generate_sap_data.py
   ```

6. Run the application:
   ```bash
   python app_lager_sap.py
   ```

7. Access the application at `http://localhost:5020` (or the configured port)

## Usage

### Dashboard Features

- **Inventory Overview**: See all products with current stock levels and status indicators
- **Category Filtering**: Filter inventory by category
- **Forecast Generation**: Generate demand forecasts with customizable parameters
- **AI Analysis**: Get AI-powered interpretation of inventory data
- **Data Import**: Upload CSV files to update inventory
- **NEW**: Clickable "Gefährdete Artikel" and "Artikel mit niedrigem Bestand" cards that open detailed views in new browser tabs
- **NEW**: Forecast-only chart that displays forecast data for selected products from the category dropdown

### New Features Documentation

#### Clickable Dashboard Elements
- The "Gefährdete Artikel" (At-risk Items) card can be clicked to open a new tab showing all items where current stock is below minimum stock level
- The "Artikel mit niedrigem Bestand" (Low Stock Items) card can be clicked to open a new tab showing all items where stock is below 50% of target but still above minimum
- Both individual count numbers and card areas are clickable for convenience

#### Product Selection Chart
- The "Nachfrageprognose" (Demand Forecast) section includes a category/product hierarchical selection
- Check products from different categories to see their forecast data in the chart
- The chart will only display forecast data for the selected products
- After generating forecasts, the chart will update to show the new forecast data for selected products

### Data Generation and Management
- The system generates 300 sample inventory records and 21,000 demand records when running `generate_sap_data.py`
- Database path is now fixed to ensure consistent access regardless of execution context
- The system includes safeguards and error handling for all operations

### SAP ERP Integration

The application includes a reference table mapping dashboard fields to SAP ERP tables:

| Dashboard Field | SAP Table | SAP Field | Description |
|----------------|-----------|-----------|-------------|
| Product ID | MARA | MATNR | Material number from material master |
| Name | MARA | MAKTX | Material short text from material master |
| Category | MARA | MATKL | Material group from material master |
| Current Stock | MARD | LABST | Storage location stock |
| Target Stock | MARD | PLSTG | Planned stock |
| Minimum Stock | MARA | BVMEH | Unit of measure from material master |
| Maximum Stock | MARA | MAXL | Maximum stock from material master |
| Avg. Monthly Demand | MBEW | AVMBM | Average consumption/month from material valuation |
| Lead Time in Days | MARC | BESKZ | Procurement type and lead time from plant data |
| Last Stock Receipt | MSEG | BUDAT | Posting date of material movement |
| Historical Demand | S091 | DATUV, WDAT, LGMNG | Historical data for forecasting from APO |
| Forecast | S092 | PERIV, WDAT, LGMNG | Forecast values from APO |

## Data Structure

The application uses three main tables:

1. **inventory**: Contains product information, stock levels, and thresholds
2. **historical_demand**: Tracks past demand patterns
3. **forecasts**: Stores generated predictions

## Customization

- To add your own data, use the CSV upload feature with the required columns
- The system supports SAP-like data fields for seamless integration concepts
- Modify the forecasting algorithm in the `call_sap_rpt1_for_forecasting` function

## Files

- `app_lager_sap.py`: Main Flask application
- `generate_sap_data.py`: Script to create sample SAP-like data
- `requirements.txt`: Python dependencies
- `sap_inventory.db`: SQLite database (not committed, generated automatically)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.