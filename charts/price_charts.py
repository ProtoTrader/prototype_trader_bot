"""
Price Charts - Generate price charts for Telegram
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import io
from typing import List, Tuple, Optional
import aiohttp
import asyncio
import logging

plt.style.use('dark_background')
logger = logging.getLogger(__name__)


class PriceChartGenerator:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate_price_chart(self, token_address: str, chain: str, 
                                  timeframe: str = '24h') -> Optional[bytes]:
        """Generate price chart for token"""
        try:
            # Get price data
            prices, timestamps = await self._get_price_data(token_address, chain, timeframe)
            
            if not prices:
                return None
            
            # Create figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
            
            # Price chart
            ax1.plot(timestamps, prices, color='#00ff41', linewidth=2)
            ax1.fill_between(timestamps, prices, alpha=0.1, color='#00ff41')
            
            # Add price indicators
            current_price = prices[-1]
            start_price = prices[0]
            price_change = ((current_price - start_price) / start_price) * 100
            
            # Style
            ax1.set_title(f'{chain} Token Price Chart - {timeframe}', 
                         fontsize=16, fontweight='bold', pad=20)
            ax1.set_ylabel('Price (USD)', fontsize=12)
            ax1.grid(True, alpha=0.2)
            
            # Add current price annotation
            ax1.annotate(f'${current_price:.6f}', 
                        xy=(timestamps[-1], current_price),
                        xytext=(10, 10), textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', fc='green' if price_change > 0 else 'red'),
                        color='white', fontweight='bold')
            
            # Volume chart (placeholder - would get real volume data)
            volumes = np.random.rand(len(timestamps)) * 1000000
            ax2.bar(timestamps, volumes, color='#00ff41', alpha=0.5)
            ax2.set_ylabel('Volume (USD)', fontsize=12)
            ax2.set_xlabel('Time', fontsize=12)
            ax2.grid(True, alpha=0.2)
            
            # Format x-axis
            if timeframe == '24h':
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            else:
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            plt.tight_layout()
            
            # Convert to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            chart_bytes = buf.read()
            plt.close()
            
            return chart_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            return None
    
    async def generate_portfolio_chart(self, trades: List[Dict]) -> Optional[bytes]:
        """Generate portfolio performance chart"""
        try:
            if not trades:
                return None
            
            # Calculate portfolio value over time
            times = []
            values = []
            
            for trade in trades:
                times.append(trade['timestamp'])
                # Calculate value based on trade data
                values.append(trade.get('current_value', 0))
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Portfolio value line
            ax.plot(times, values, color='#00ff41', linewidth=3, label='Portfolio Value')
            ax.fill_between(times, values, alpha=0.1, color='#00ff41')
            
            # Calculate stats
            initial_value = values[0] if values else 0
            current_value = values[-1] if values else 0
            pnl = current_value - initial_value
            pnl_percent = (pnl / initial_value * 100) if initial_value > 0 else 0
            
            # Style
            ax.set_title('Portfolio Performance', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Value (USD)', fontsize=12)
            ax.set_xlabel('Date', fontsize=12)
            ax.grid(True, alpha=0.2)
            
            # Add PnL annotation
            color = 'green' if pnl >= 0 else 'red'
            ax.text(0.02, 0.95, f'PnL: ${pnl:,.2f} ({pnl_percent:+.2f}%)',
                   transform=ax.transAxes, fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', fc=color, alpha=0.8),
                   color='white', verticalalignment='top')
            
            # Format dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Convert to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            chart_bytes = buf.read()
            plt.close()
            
            return chart_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate portfolio chart: {e}")
            return None
    
    async def _get_price_data(self, token_address: str, chain: str, 
                            timeframe: str) -> Tuple[List[float], List[datetime]]:
        """Get historical price data"""
        try:
            # This would fetch from DexScreener, CoinGecko, etc.
            # For now, generate sample data
            
            hours = 24 if timeframe == '24h' else 168  # 7 days
            
            # Generate timestamps
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            timestamps = []
            current = start_time
            
            while current <= end_time:
                timestamps.append(current)
                current += timedelta(minutes=15 if timeframe == '24h' else 60)
            
            # Generate sample price data with realistic movement
            base_price = 0.0001
            prices = []
            price = base_price
            
            for _ in timestamps:
                # Random walk with trend
                change = np.random.normal(0.0002, 0.01)
                price *= (1 + change)
                price = max(price, base_price * 0.5)  # Floor at 50% of base
                prices.append(price)
            
            return prices, timestamps
            
        except Exception as e:
            logger.error(f"Failed to get price data: {e}")
            return [], []