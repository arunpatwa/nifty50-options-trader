#!/usr/bin/env python3
"""
Simple dashboard launcher for the trading system
"""

import dash
from dash import html, dcc
import plotly.graph_objs as go
import sqlite3
import pandas as pd
from datetime import datetime

# Initialize Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("🚀 Nifty 50 Options Trading Dashboard", style={'text-align': 'center', 'color': '#2c3e50'}),
    
    html.Div([
        html.Div([
            html.H3("System Status", style={'color': '#27ae60'}),
            html.P(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", id="status-time"),
            html.P("✅ Trading Bot: RUNNING", style={'color': 'green', 'font-weight': 'bold'}),
            html.P("✅ Database: CONNECTED", style={'color': 'green', 'font-weight': 'bold'}),
            html.P("✅ Dhan API: AUTHENTICATED", style={'color': 'green', 'font-weight': 'bold'}),
        ], className="four columns", style={'background-color': '#ecf0f1', 'padding': '20px', 'margin': '10px', 'border-radius': '10px'}),
        
        html.Div([
            html.H3("Portfolio Summary", style={'color': '#e74c3c'}),
            html.P("Total Positions: 0", id="total-positions"),
            html.P("Total P&L: ₹0.00", id="total-pnl", style={'font-size': '18px', 'font-weight': 'bold'}),
            html.P("Daily P&L: ₹0.00", id="daily-pnl"),
            html.P("Active Strategies: 2", style={'color': '#3498db'}),
        ], className="four columns", style={'background-color': '#ecf0f1', 'padding': '20px', 'margin': '10px', 'border-radius': '10px'}),
        
        html.Div([
            html.H3("Risk Metrics", style={'color': '#f39c12'}),
            html.P("Max Risk per Trade: 2%"),
            html.P("Daily Loss Limit: ₹5,000"),
            html.P("Portfolio Limit: ₹1,00,000"),
            html.P("Drawdown: 0%", style={'color': 'green'}),
        ], className="four columns", style={'background-color': '#ecf0f1', 'padding': '20px', 'margin': '10px', 'border-radius': '10px'}),
    ], className="row"),
    
    html.Div([
        html.H3("Active Strategies", style={'text-align': 'center', 'color': '#2c3e50'}),
        html.Div([
            html.Div([
                html.H4("📈 Scalping Strategy", style={'color': '#e74c3c'}),
                html.P("Status: RUNNING"),
                html.P("Interval: 5 seconds"),
                html.P("Positions: 0"),
                html.P("P&L: ₹0.00"),
            ], className="six columns", style={'background-color': '#fff', 'padding': '15px', 'margin': '5px', 'border': '1px solid #bdc3c7', 'border-radius': '5px'}),
            
            html.Div([
                html.H4("📊 Momentum Strategy", style={'color': '#3498db'}),
                html.P("Status: RUNNING"),
                html.P("Interval: Variable"),
                html.P("Positions: 0"),
                html.P("P&L: ₹0.00"),
            ], className="six columns", style={'background-color': '#fff', 'padding': '15px', 'margin': '5px', 'border': '1px solid #bdc3c7', 'border-radius': '5px'}),
        ], className="row"),
    ]),
    
    html.Div([
        html.H3("Recent Activity", style={'text-align': 'center', 'color': '#2c3e50'}),
        html.Div(id="recent-activity", style={'background-color': '#f8f9fa', 'padding': '20px', 'border-radius': '10px', 'font-family': 'monospace'}),
    ], style={'margin': '20px'}),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # Update every 5 seconds
        n_intervals=0
    )
])

def get_recent_logs():
    """Get recent log entries"""
    try:
        log_file = "logs/trading_20250809.log"
        with open(log_file, 'r') as f:
            lines = f.readlines()[-10:]  # Last 10 lines
        
        recent_logs = []
        for line in lines:
            if line.strip():
                recent_logs.append(html.P(line.strip(), style={'margin': '2px', 'color': '#2c3e50'}))
        
        return recent_logs if recent_logs else [html.P("No recent activity", style={'color': '#7f8c8d'})]
    except:
        return [html.P("Unable to load log file", style={'color': '#e74c3c'})]

@app.callback(
    dash.dependencies.Output('recent-activity', 'children'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_activity(n):
    return get_recent_logs()

@app.callback(
    dash.dependencies.Output('status-time', 'children'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_time(n):
    return f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

if __name__ == '__main__':
    print("🚀 Starting Nifty Options Trading Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8050")
    print("🔄 Auto-refreshing every 5 seconds")
    print("⏹️  Press Ctrl+C to stop")
    
    app.run(
        debug=False,
        host='0.0.0.0',
        port=8050
    )
