# SAP Lagerbestand Management System - Documentation

## Project Overview

This project simulates an SAP ERP inventory management system with forecasting capabilities and AI-powered analysis. It provides a web-based interface for managing warehouse inventory with SAP-like data structures and processes.

## Project Structure

```
lagerbestand_SAP/
├── app_lager_sap.py          # Main Flask application with UI and API endpoints
├── generate_sap_data.py      # Script to generate SAP-like sample data
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── LICENSE                   # License information
├── .gitignore               # Git ignore rules
└── Documentation/
    └── project_structure.md  # This file
```

## Application Architecture

### Backend (Flask Application)
- **Framework**: Flask with CORS support
- **Database**: SQLite with three main tables:
  1. `inventory` - Product information, stock levels, thresholds
  2. `historical_demand` - Past demand patterns
  3. `forecasts` - Generated predictions

### Frontend
- **Template Engine**: Jinja2 (embedded in Flask route)
- **Styling**: Tailwind CSS via CDN
- **Charts**: Chart.js with date adapter
- **Icons**: Font Awesome
- **API Communication**: Native JavaScript fetch API

### Data Generation
- **Faker Library**: Generates realistic German SAP-like data
- **Data Types**: 300 sample products across multiple categories
- **Demand Patterns**: Simulated historical demand data

## Key Features and Functionality

### 1. Dashboard Views
- Real-time inventory status
- Category filtering
- Key metrics (total products, at-risk items, low stock items)

### 2. Forecasting Engine
- Demand prediction algorithms
- Configurable forecast duration
- Confidence levels
- SAP RPT-1 simulation

### 3. SAP Integration Reference
- Field mapping to actual SAP ERP tables
- MARA, MARD, MBEW, MARC, MSEG table references
- S091/S092 APO forecasting table links

### 4. Data Management
- CSV import functionality
- Historical data tracking
- Automatic backup before updates

### 5. AI Analysis
- Ollama integration for insights
- German language interpretation
- Inventory optimization recommendations

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard page |
| GET | `/api/inventory` | Get all inventory items |
| GET | `/api/inventory/<product_id>` | Get specific inventory item |
| PUT | `/api/inventory/<product_id>` | Update specific inventory item |
| GET | `/api/inventory/stats` | Get inventory statistics |
| GET | `/api/demand/<product_id>` | Get historical demand for product |
| GET | `/api/historical_demand_all` | Get all historical demand |
| GET | `/api/forecasts` | Get all forecasts |
| GET | `/api/forecasts/<product_id>` | Get forecasts for specific product |
| POST | `/api/generate_forecasts` | Generate new demand forecasts |
| POST | `/api/optimize_inventory` | Optimize inventory based on forecasts |
| POST | `/api/interpret_results` | Get AI analysis of results |
| POST | `/api/clear_forecasts` | Clear forecast data |
| POST | `/api/upload_inventory` | Upload inventory data from CSV |

## Configuration

### Environment Dependencies
- Python 3.8+
- Ollama (for AI functionality)
- SQLite (included with Python)

### Default Settings
- Server runs on `http://0.0.0.0:5001`
- Database file: `sap_inventory.db` (generated automatically)
- Default model for AI: tries `gpt-oss:20b-cloud` first, then falls back to local models (llama3, mistral, gemma, phi)

## SAP ERP Mapping

The application maps dashboard fields to actual SAP ERP tables:

- **Material Master (MARA)**: Product ID, description, category
- **Material Staging (MARD)**: Stock levels, target values
- **Material Valuation (MBEW)**: Average monthly demand
- **Plant Data (MARC)**: Lead times
- **Material Document (MSEG)**: Last stock receipt
- **APO Forecast Tables (S091, S092)**: Historical and forecast data

## Data Schema

### Inventory Table
- `product_id`: Unique product identifier (MATNR in SAP)
- `product_name`: Product description (MAKTX in SAP)
- `category/kategorie`: Product category (MATKL in SAP)
- `current_stock`: Current inventory level
- `target_stock`: Target inventory level
- `min_stock`: Minimum stock threshold
- `max_stock`: Maximum stock threshold
- `avg_monthly_demand`: Average historical demand
- `lead_time_days`: Time to replenish stock
- `last_restock_date`: Date of last stock receipt
- `seasonality_factor`: Seasonal demand weighting

### Historical Demand Table
- `date`: Date of demand record
- `product_id`: Reference to inventory item
- `daily_demand`: Units demanded on that day
- `price`: Product price (for analysis)
- `marketing_spend`: Marketing spend on that day
- `seasonal_factor`: Seasonal adjustment factor

### Forecasts Table
- `product_id`: Reference to inventory item
- `forecast_date`: Date of forecast
- `predicted_demand`: Forecasted demand value
- `confidence_level`: Confidence in prediction
- `created_at`: Timestamp of forecast creation

## Development Notes

### Forecasting Algorithm
The application simulates SAP RPT-1 forecasting using:
- Historical demand patterns
- Trend analysis
- Seasonal adjustments
- Statistical modeling

### UI/UX Features
- Responsive design with Tailwind CSS
- Interactive charts with real-time updates
- Hierarchical category/product selection
- Progress indicators for long-running operations

### Error Handling
- Comprehensive API error responses
- Client-side validation
- Graceful fallbacks for Ollama issues
- Database connection error handling

## Deployment Considerations

1. Ensure Ollama is running before starting the application
2. Configure appropriate database backup procedures
3. Set up proper SSL for production deployments
4. Configure appropriate logging for production
5. Consider using a production WSGI server (Gunicorn, uWSGI) instead of Flask's development server

## Troubleshooting

- If Ollama fails, AI features will use fallback models
- Database is auto-generated if not found
- Invalid CSV data will show appropriate error messages
- Check browser console for JavaScript errors