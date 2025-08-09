"""
Web-based dashboard for monitoring the Nifty options trading bot
"""

import asyncio
from typing import Dict, List, Any
import json
from datetime import datetime
import threading

# Dashboard framework imports (install if needed)
try:
    import dash
    from dash import dcc, html, Input, Output, callback
    import plotly.graph_objs as go
    import plotly.express as px
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

from src.utils.logger import TradingLogger
from config.settings import settings

class TradingDashboard:
    """Web dashboard for monitoring trading activities"""
    
    def __init__(self, trading_bot=None):
        self.logger = TradingLogger(__name__)
        self.trading_bot = trading_bot
        self.app = None
        
        # Dashboard data
        self.dashboard_data = {
            'nifty_prices': [],
            'positions': [],
            'orders': [],
            'pnl_history': [],
            'strategy_performance': {},
            'market_status': {},
            'risk_metrics': {}
        }
        
        # Update intervals
        self.update_interval = 5000  # 5 seconds in milliseconds
        
        if DASH_AVAILABLE:
            self._create_dashboard()
    
    def _create_dashboard(self):
        """Create the Dash web application"""
        try:
            self.app = dash.Dash(__name__, title="Nifty Options Trader")
            
            # Define layout
            self.app.layout = html.Div([
                # Header
                html.Div([
                    html.H1("Nifty 50 Options Automated Trader", 
                           className="dashboard-title",
                           style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'})
                ]),
                
                # Status cards row
                html.Div([
                    html.Div([
                        html.H3("Market Status", className="card-title"),
                        html.Div(id="market-status", className="card-content")
                    ], className="status-card", style={'width': '23%', 'display': 'inline-block', 'margin': '1%'}),
                    
                    html.Div([
                        html.H3("Active Positions", className="card-title"),
                        html.Div(id="positions-count", className="card-content")
                    ], className="status-card", style={'width': '23%', 'display': 'inline-block', 'margin': '1%'}),
                    
                    html.Div([
                        html.H3("Daily P&L", className="card-title"),
                        html.Div(id="daily-pnl", className="card-content")
                    ], className="status-card", style={'width': '23%', 'display': 'inline-block', 'margin': '1%'}),
                    
                    html.Div([
                        html.H3("Total P&L", className="card-title"),
                        html.Div(id="total-pnl", className="card-content")
                    ], className="status-card", style={'width': '23%', 'display': 'inline-block', 'margin': '1%'})
                ], style={'width': '100%', 'textAlign': 'center'}),
                
                # Charts row
                html.Div([
                    # Nifty price chart
                    html.Div([
                        dcc.Graph(id="nifty-price-chart", style={'height': '400px'})
                    ], style={'width': '50%', 'display': 'inline-block'}),
                    
                    # P&L chart
                    html.Div([
                        dcc.Graph(id="pnl-chart", style={'height': '400px'})
                    ], style={'width': '50%', 'display': 'inline-block'})
                ]),
                
                # Tables row
                html.Div([
                    # Positions table
                    html.Div([
                        html.H3("Current Positions"),
                        html.Div(id="positions-table")
                    ], style={'width': '50%', 'display': 'inline-block', 'padding': '20px'}),
                    
                    # Recent orders table
                    html.Div([
                        html.H3("Recent Orders"),
                        html.Div(id="orders-table")
                    ], style={'width': '50%', 'display': 'inline-block', 'padding': '20px'})
                ]),
                
                # Strategy performance row
                html.Div([
                    html.H3("Strategy Performance"),
                    html.Div(id="strategy-performance")
                ], style={'padding': '20px'}),
                
                # Auto-refresh interval
                dcc.Interval(
                    id='interval-component',
                    interval=self.update_interval,
                    n_intervals=0
                )
            ])
            
            # Register callbacks
            self._register_callbacks()
            
            self.logger.logger.info("Dashboard created successfully")
            
        except Exception as e:
            self.logger.logger.error(f"Error creating dashboard: {e}")
    
    def _register_callbacks(self):
        """Register Dash callbacks for real-time updates"""
        
        @self.app.callback(
            [Output('market-status', 'children'),
             Output('positions-count', 'children'),
             Output('daily-pnl', 'children'),
             Output('total-pnl', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_status_cards(n):
            return self._update_status_cards()
        
        @self.app.callback(
            Output('nifty-price-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_nifty_chart(n):
            return self._create_nifty_chart()
        
        @self.app.callback(
            Output('pnl-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_pnl_chart(n):
            return self._create_pnl_chart()
        
        @self.app.callback(
            Output('positions-table', 'children'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_positions_table(n):
            return self._create_positions_table()
        
        @self.app.callback(
            Output('orders-table', 'children'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_orders_table(n):
            return self._create_orders_table()
        
        @self.app.callback(
            Output('strategy-performance', 'children'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_strategy_performance(n):
            return self._create_strategy_performance()
    
    def _update_status_cards(self):
        """Update status card data"""
        try:
            # Update dashboard data
            self._refresh_dashboard_data()
            
            # Market status
            market_status = "🟢 Open" if self.dashboard_data['market_status'].get('is_open') else "🔴 Closed"
            
            # Positions count
            positions_count = len(self.dashboard_data['positions'])
            
            # Daily P&L
            daily_pnl = self.dashboard_data['risk_metrics'].get('daily_pnl', 0)
            daily_pnl_color = 'green' if daily_pnl >= 0 else 'red'
            daily_pnl_text = html.Span(f"₹{daily_pnl:.2f}", style={'color': daily_pnl_color, 'fontSize': '24px', 'fontWeight': 'bold'})
            
            # Total P&L
            total_pnl = self.dashboard_data['risk_metrics'].get('total_pnl', 0)
            total_pnl_color = 'green' if total_pnl >= 0 else 'red'
            total_pnl_text = html.Span(f"₹{total_pnl:.2f}", style={'color': total_pnl_color, 'fontSize': '24px', 'fontWeight': 'bold'})
            
            return market_status, str(positions_count), daily_pnl_text, total_pnl_text
            
        except Exception as e:
            self.logger.logger.error(f"Error updating status cards: {e}")
            return "Error", "Error", "Error", "Error"
    
    def _create_nifty_chart(self):
        """Create Nifty price chart"""
        try:
            if not self.dashboard_data['nifty_prices']:
                return go.Figure()
            
            df_data = self.dashboard_data['nifty_prices'][-100:]  # Last 100 points
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[point['timestamp'] for point in df_data],
                y=[point['price'] for point in df_data],
                mode='lines',
                name='Nifty 50',
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title='Nifty 50 Price Movement',
                xaxis_title='Time',
                yaxis_title='Price',
                showlegend=True,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.logger.error(f"Error creating Nifty chart: {e}")
            return go.Figure()
    
    def _create_pnl_chart(self):
        """Create P&L chart"""
        try:
            if not self.dashboard_data['pnl_history']:
                return go.Figure()
            
            df_data = self.dashboard_data['pnl_history'][-50:]  # Last 50 points
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[point['timestamp'] for point in df_data],
                y=[point['cumulative_pnl'] for point in df_data],
                mode='lines',
                name='Cumulative P&L',
                line=dict(color='green', width=2),
                fill='tonexty'
            ))
            
            fig.update_layout(
                title='Cumulative P&L',
                xaxis_title='Time',
                yaxis_title='P&L (₹)',
                showlegend=True,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.logger.error(f"Error creating P&L chart: {e}")
            return go.Figure()
    
    def _create_positions_table(self):
        """Create positions table"""
        try:
            if not self.dashboard_data['positions']:
                return html.P("No active positions")
            
            # Create table rows
            rows = []
            for pos in self.dashboard_data['positions']:
                pnl_color = 'green' if pos.get('total_pnl', 0) >= 0 else 'red'
                rows.append(html.Tr([
                    html.Td(pos.get('symbol', 'N/A')),
                    html.Td(str(pos.get('quantity', 0))),
                    html.Td(f"₹{pos.get('avg_price', 0):.2f}"),
                    html.Td(f"₹{pos.get('market_price', 0):.2f}"),
                    html.Td(f"₹{pos.get('total_pnl', 0):.2f}", style={'color': pnl_color}),
                    html.Td(pos.get('strategy', 'N/A'))
                ]))
            
            table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Symbol'),
                        html.Th('Quantity'),
                        html.Th('Avg Price'),
                        html.Th('Market Price'),
                        html.Th('P&L'),
                        html.Th('Strategy')
                    ])
                ]),
                html.Tbody(rows)
            ], style={'width': '100%', 'textAlign': 'center'})
            
            return table
            
        except Exception as e:
            self.logger.logger.error(f"Error creating positions table: {e}")
            return html.P("Error loading positions")
    
    def _create_orders_table(self):
        """Create recent orders table"""
        try:
            if not self.dashboard_data['orders']:
                return html.P("No recent orders")
            
            # Get last 10 orders
            recent_orders = self.dashboard_data['orders'][-10:]
            
            rows = []
            for order in recent_orders:
                status_color = {
                    'FILLED': 'green',
                    'OPEN': 'blue',
                    'CANCELLED': 'red',
                    'REJECTED': 'red'
                }.get(order.get('status'), 'black')
                
                rows.append(html.Tr([
                    html.Td(order.get('symbol', 'N/A')),
                    html.Td(order.get('side', 'N/A')),
                    html.Td(str(order.get('quantity', 0))),
                    html.Td(f"₹{order.get('price', 0):.2f}"),
                    html.Td(order.get('status', 'N/A'), style={'color': status_color}),
                    html.Td(order.get('created_at', 'N/A')[:19] if order.get('created_at') else 'N/A')
                ]))
            
            table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th('Symbol'),
                        html.Th('Side'),
                        html.Th('Quantity'),
                        html.Th('Price'),
                        html.Th('Status'),
                        html.Th('Time')
                    ])
                ]),
                html.Tbody(rows)
            ], style={'width': '100%', 'textAlign': 'center'})
            
            return table
            
        except Exception as e:
            self.logger.logger.error(f"Error creating orders table: {e}")
            return html.P("Error loading orders")
    
    def _create_strategy_performance(self):
        """Create strategy performance display"""
        try:
            if not self.dashboard_data['strategy_performance']:
                return html.P("No strategy data available")
            
            strategy_cards = []
            for strategy_name, performance in self.dashboard_data['strategy_performance'].items():
                win_rate = performance.get('win_rate', 0)
                win_rate_color = 'green' if win_rate >= 60 else 'orange' if win_rate >= 40 else 'red'
                
                card = html.Div([
                    html.H4(strategy_name),
                    html.P(f"Trades: {performance.get('total_trades', 0)}"),
                    html.P(f"P&L: ₹{performance.get('pnl_today', 0):.2f}"),
                    html.P(f"Win Rate: {win_rate:.1f}%", style={'color': win_rate_color}),
                    html.P(f"Status: {'🟢' if performance.get('running') else '🔴'}")
                ], style={
                    'border': '1px solid #ddd',
                    'borderRadius': '5px',
                    'padding': '15px',
                    'margin': '10px',
                    'display': 'inline-block',
                    'width': '200px',
                    'textAlign': 'center'
                })
                
                strategy_cards.append(card)
            
            return html.Div(strategy_cards)
            
        except Exception as e:
            self.logger.logger.error(f"Error creating strategy performance: {e}")
            return html.P("Error loading strategy performance")
    
    def _refresh_dashboard_data(self):
        """Refresh dashboard data from trading bot"""
        try:
            if not self.trading_bot:
                return
            
            # Update market status
            from src.utils.helpers import get_market_status
            self.dashboard_data['market_status'] = get_market_status()
            
            # Update Nifty prices
            nifty_price = self.trading_bot.data_manager.get_nifty_price()
            if nifty_price:
                self.dashboard_data['nifty_prices'].append({
                    'timestamp': datetime.now(),
                    'price': nifty_price
                })
                
                # Keep only last 200 points
                if len(self.dashboard_data['nifty_prices']) > 200:
                    self.dashboard_data['nifty_prices'] = self.dashboard_data['nifty_prices'][-200:]
            
            # Update positions
            positions = self.trading_bot.position_manager.get_positions()
            self.dashboard_data['positions'] = [pos.to_dict() for pos in positions.values()]
            
            # Update orders (mock data for now)
            # In real implementation, get from order manager
            
            # Update P&L history
            total_pnl = self.trading_bot.position_manager.get_total_pnl()
            daily_pnl = self.trading_bot.position_manager.daily_pnl
            
            self.dashboard_data['pnl_history'].append({
                'timestamp': datetime.now(),
                'cumulative_pnl': total_pnl,
                'daily_pnl': daily_pnl
            })
            
            # Keep only last 100 points
            if len(self.dashboard_data['pnl_history']) > 100:
                self.dashboard_data['pnl_history'] = self.dashboard_data['pnl_history'][-100:]
            
            # Update risk metrics
            self.dashboard_data['risk_metrics'] = self.trading_bot.position_manager.get_risk_summary()
            
            # Update strategy performance
            self.dashboard_data['strategy_performance'] = {}
            for strategy_name, strategy in self.trading_bot.strategies.items():
                self.dashboard_data['strategy_performance'][strategy_name] = strategy.get_performance_summary()
                
        except Exception as e:
            self.logger.logger.error(f"Error refreshing dashboard data: {e}")
    
    def run(self, host='localhost', port=8050, debug=False):
        """Run the dashboard"""
        if not DASH_AVAILABLE:
            self.logger.logger.error("Dash not available. Install with: pip install dash plotly")
            return
        
        if not self.app:
            self.logger.logger.error("Dashboard not created")
            return
        
        try:
            self.logger.logger.info(f"Starting dashboard on http://{host}:{port}")
            self.app.run_server(host=host, port=port, debug=debug, threaded=True)
            
        except Exception as e:
            self.logger.logger.error(f"Error running dashboard: {e}")

def create_dashboard(trading_bot=None):
    """Create and return dashboard instance"""
    return TradingDashboard(trading_bot)
