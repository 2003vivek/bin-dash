# Binance Futures Analytics Platform

A real-time analytics platform for Binance futures trading data with WebSocket ingestion, statistical analysis, and interactive visualization.

## Features

### Data Ingestion
- Real-time WebSocket connection to Binance futures streams
- Support for multiple symbols simultaneously
- Automatic resampling to OHLC bars (1s, 1m, 5m)
- Raw tick data storage in SQLite

### Analytics
- **Price Statistics**: Mean, std, min, max, percentiles
- **Z-Score**: Mean reversion indicator
- **Spread**: Price difference between pairs
- **Hedge Ratio**: OLS regression for pair trading
- **Rolling Correlation**: Dynamic correlation over rolling windows
- **ADF Test**: Augmented Dickey-Fuller test for stationarity

### Alerts
- Custom alert rules (e.g., z_score > 2)
- Real-time alert notifications via WebSocket
- Alert history tracking

### Visualization
- Interactive real-time price charts
- Z-score visualization with threshold lines
- Spread charts
- Correlation plots
- Price statistics dashboard

### Data Export
- Export tick data as CSV or NDJSON
- Export OHLC data
- OHLC data upload functionality

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (HTML/CSS/JS)            │
│              Real-time Dashboard with Plotly        │
└────────────────────┬────────────────────────────────┘
                     │ WebSocket / REST API
┌────────────────────▼────────────────────────────────┐
│              Django Backend                         │
│  ┌──────────────────────────────────────────────┐  │
│  │ WebSocket Consumers (Django Channels)        │  │
│  │ - Binance Data Ingestion                     │  │
│  │ - Analytics Broadcasting                     │  │
│  │ - Alert Notifications                        │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │ Analytics Engine                             │  │
│  │ - Statistical Computations                   │  │
│  │ - Resampling                                 │  │
│  │ - Alert Evaluation                           │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │ Data Storage (SQLite)                        │  │
│  │ - TickData                                   │  │
│  │ - OHLCData                                   │  │
│  │ - AnalyticsCache                             │  │
│  │ - AlertRule                                  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         Binance WebSocket Streams                   │
│    wss://fstream.binance.com/stream                 │
└─────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd project-folder
   ```

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

## Running the Application

### Single Command Execution


The application will be available at:
- **Main Dashboard**: http://127.0.0.1:8000
- **Admin Panel**: http://127.0.0.1:8000/admin
- **API Endpoints**: http://127.0.0.1:8000/api/

### Using Uvicorn (Required for WebSocket)



**Option 1: Use the start script (Recommended)**
```bash
./start_server.sh
```
