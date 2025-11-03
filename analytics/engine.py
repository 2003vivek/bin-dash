"""
Analytics Engine for statistical computations
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS
from datetime import timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Core analytics computation engine"""
    
    def __init__(self):
        self.tick_buffers = defaultdict(list)  # In-memory buffers for resampling
        
    def calculate_price_stats(self, prices):
        """Calculate price statistics"""
        if not prices or len(prices) < 2:
            return {}
            
        prices_array = np.array(prices)
        return {
            'mean': float(np.mean(prices_array)),
            'std': float(np.std(prices_array)),
            'min': float(np.min(prices_array)),
            'max': float(np.max(prices_array)),
            'median': float(np.median(prices_array)),
            'p25': float(np.percentile(prices_array, 25)),
            'p75': float(np.percentile(prices_array, 75)),
            'count': len(prices),
        }
        
    def calculate_z_score(self, prices, window=100):
        """Calculate z-score for mean reversion"""
        if len(prices) < window:
            window = len(prices)
            
        recent_prices = prices[-window:]
        mean = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        if std == 0:
            return 0.0
            
        current_price = prices[-1]
        z_score = (current_price - mean) / std
        return float(z_score)
        
    def calculate_spread(self, prices1, prices2):
        """Calculate spread between two price series (for pairs trading)"""
        if len(prices1) != len(prices2):
            min_len = min(len(prices1), len(prices2))
            prices1 = prices1[:min_len]
            prices2 = prices2[:min_len]
            
        spread = np.array(prices1) - np.array(prices2)
        return {
            'mean': float(np.mean(spread)),
            'std': float(np.std(spread)),
            'min': float(np.min(spread)),
            'max': float(np.max(spread)),
            'current': float(spread[-1]) if len(spread) > 0 else 0.0,
            'values': spread.tolist()[-100:],  # Last 100 values for chart
        }
        
    def calculate_price_spread(self, prices):
        """Calculate price spread (high-low) for a single symbol"""
        if not prices or len(prices) < 2:
            return {}
        prices_array = np.array(prices)
        recent_window = prices_array[-100:] if len(prices_array) >= 100 else prices_array
        return {
            'high': float(np.max(recent_window)),
            'low': float(np.min(recent_window)),
            'spread': float(np.max(recent_window) - np.min(recent_window)),
            'current_price': float(prices_array[-1]),
            'spread_pct': float((np.max(recent_window) - np.min(recent_window)) / np.mean(recent_window) * 100) if np.mean(recent_window) > 0 else 0.0,
        }
        
    def calculate_hedge_ratio(self, prices1, prices2, method='ols'):
        """Calculate hedge ratio using OLS regression"""
        if len(prices1) != len(prices2) or len(prices1) < 10:
            return None
            
        min_len = min(len(prices1), len(prices2))
        y = np.array(prices1[:min_len])
        x = np.array(prices2[:min_len])
        
        try:
            if method == 'ols':
                # OLS: y = alpha + beta * x
                # Add intercept
                x_with_const = np.column_stack([np.ones(len(x)), x])
                model = OLS(y, x_with_const).fit()
                
                alpha = float(model.params[0])  # Intercept
                beta = float(model.params[1])   # Hedge ratio (slope)
                r_squared = float(model.rsquared)
                
                # Calculate fitted values for plotting
                fitted_values = model.fittedvalues.tolist()
                
                return {
                    'hedge_ratio': beta,
                    'alpha': alpha,
                    'r_squared': r_squared,
                    'intercept': alpha,
                    'slope': beta,
                    'fitted_values': fitted_values[-100:],  # Last 100 for visualization
                    'actual_values': y.tolist()[-100:],
                    'x_values': x.tolist()[-100:],
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Error calculating hedge ratio: {e}")
            return None
            
    def calculate_rolling_correlation(self, prices1, prices2, window=100):
        """Calculate rolling correlation"""
        if len(prices1) != len(prices2) or len(prices1) < window:
            return None
            
        min_len = min(len(prices1), len(prices2))
        series1 = pd.Series(prices1[:min_len])
        series2 = pd.Series(prices2[:min_len])
        
        rolling_corr = series1.rolling(window=window).corr(series2)
        
        return {
            'current': float(rolling_corr.iloc[-1]) if not rolling_corr.empty else 0.0,
            'mean': float(rolling_corr.mean()) if not rolling_corr.empty else 0.0,
            'std': float(rolling_corr.std()) if not rolling_corr.empty else 0.0,
            'values': rolling_corr.dropna().tolist()[-50:],  # Last 50 values
        }
        
    def adf_test(self, prices):
        """Augmented Dickey-Fuller test for stationarity"""
        if len(prices) < 10:
            return None
            
        try:
            result = adfuller(prices)
            return {
                'adf_statistic': float(result[0]),
                'p_value': float(result[1]),
                'critical_values': {k: float(v) for k, v in result[4].items()},
                'is_stationary': result[1] < 0.05,  # p-value < 0.05 suggests stationarity
            }
        except Exception as e:
            logger.error(f"Error in ADF test: {e}")
            return None
            
    def resample_ticks(self, ticks, timeframe):
        """Resample tick data to OHLC bars"""
        if not ticks:
            return []
            
        # Convert ticks to DataFrame
        df = pd.DataFrame([{
            'timestamp': t.timestamp,
            'price': t.price,
            'size': t.size,
        } for t in ticks])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample based on timeframe
        if timeframe == '1s':
            freq = '1s'  # Changed from '1S' to '1s'
        elif timeframe == '1m':
            freq = '1min'  # Changed from '1T' to '1min'
        elif timeframe == '5m':
            freq = '5min'  # Changed from '5T' to '5min'
        else:
            return []
            
        # Resample to OHLC
        resampled = df['price'].resample(freq).ohlc()
        volume = df['size'].resample(freq).sum()
        
        # Combine
        resampled['volume'] = volume
        
        # Convert to list of dicts
        bars = []
        for ts, row in resampled.dropna().iterrows():
            bars.append({
                'timestamp': ts,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
            })
            
        return bars
        
    def calculate_pair_analytics(self, symbol1_prices, symbol2_prices, window=100):
        """Calculate all pair analytics"""
        return {
            'spread': self.calculate_spread(symbol1_prices, symbol2_prices),
            'hedge_ratio': self.calculate_hedge_ratio(symbol1_prices, symbol2_prices),
            'correlation': self.calculate_rolling_correlation(symbol1_prices, symbol2_prices, window),
            'adf_test': self.adf_test([p1 - p2 for p1, p2 in zip(symbol1_prices, symbol2_prices)]),
        }

