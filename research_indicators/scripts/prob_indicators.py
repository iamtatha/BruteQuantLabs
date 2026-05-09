import sys
from pathlib import Path

# Root = parent of current file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from analysis_scripts.utils.primary_indicators import add_indicators
from analysis_scripts.utils.advanced_indicators import add_advanced_indicators


import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from scipy.spatial.distance import euclidean
from scipy.spatial.distance import cdist
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indicator_probabilities.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)




def calculate_indicator_effectiveness(df, indicators, gap_days=5, 
                                     price_change_threshold=0.02,
                                     pattern_window=10,
                                     top_k_patterns=5,
                                     log=False,
                                     scaler_usage=False,
                                     max_lookback=1000):
    """
    Calculate effectiveness of technical indicators by finding similar historical patterns.
    OPTIMIZED VERSION with vectorized operations.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with OHLC data and indicators
    indicators : list
        List of indicator column names to evaluate
    gap_days : int
        Number of days ahead to predict price movement
    price_change_threshold : float
        Minimum price change % to consider a prediction successful (e.g., 0.02 = 2%)
    pattern_window : int
        Number of periods to look back for pattern matching
    top_k_patterns : int
        Number of most similar historical patterns to use for prediction
    log : bool
        Enable detailed logging
    scaler_usage : bool
        Use sklearn MinMaxScaler for normalization (more robust for extreme values)
    max_lookback : int
        Maximum number of periods to look back for pattern matching (speeds up calculation)
    
    Returns:
    --------
    df_predictions : pd.DataFrame
        Original dataframe with added prediction columns
    summary : dict
        Dictionary with effectiveness metrics for each indicator
    """
    
    if log:
        logger.info("Starting indicator effectiveness calculation")
        logger.info(f"Parameters: gap_days={gap_days}, threshold={price_change_threshold}, "
                   f"pattern_window={pattern_window}, top_k={top_k_patterns}, scaler={scaler_usage}")
    
    df = df.copy()
    df_predictions = df.copy()
    summary = {}
    
    # Ensure we have enough data
    min_required = pattern_window + gap_days
    if len(df) < min_required:
        error_msg = f"Need at least {min_required} rows, got {len(df)}"
        if log:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    if log:
        logger.info(f"Total rows in dataframe: {len(df)}")
        logger.info(f"Evaluating {len(indicators)} indicators: {indicators}")
    
    # Initialize scaler if needed
    scaler = MinMaxScaler() if scaler_usage else None
    
    for idx, indicator in enumerate(indicators):
        if log:
            logger.info(f"Processing indicator {idx+1}/{len(indicators)}: {indicator}")
        
        if indicator not in df.columns:
            warning_msg = f"Warning: {indicator} not found in dataframe, skipping"
            if log:
                logger.warning(warning_msg)
            else:
                print(warning_msg)
            continue
        
        # Initialize prediction arrays
        n_predictions = len(df) - pattern_window - gap_days
        expected_prices = np.full(n_predictions, np.nan)
        actual_returns = np.full(n_predictions, np.nan)
        predicted_returns = np.full(n_predictions, np.nan)
        success_flags = np.full(n_predictions, np.nan)
        max_returns_within_gap = np.full(n_predictions, np.nan)
        
        # Extract indicator values
        indicator_values = df[indicator].values
        close_prices = df['close'].values
        
        # Pre-compute all valid patterns and their normalized versions
        if log:
            logger.info(f"  Pre-computing patterns...")
        
        # Create sliding windows for all patterns
        valid_patterns = []
        valid_indices = []
        
        for i in range(pattern_window, len(df) - gap_days):
            pattern = indicator_values[i-pattern_window:i]
            if not np.isnan(pattern).any():
                # Normalize
                if scaler_usage:
                    pattern_norm = scaler.fit_transform(pattern.reshape(-1, 1)).flatten()
                else:
                    pattern_norm = (pattern - np.min(pattern)) / (np.max(pattern) - np.min(pattern) + 1e-9)
                
                valid_patterns.append(pattern_norm)
                valid_indices.append(i)
        
        valid_patterns = np.array(valid_patterns)
        valid_indices = np.array(valid_indices)
        
        if log:
            logger.info(f"  Found {len(valid_patterns)} valid patterns")
            logger.info(f"  Computing predictions...")
        
        # Process each prediction point
        for pred_idx, i in enumerate(valid_indices):
            # Current pattern
            current_pattern_norm = valid_patterns[pred_idx]
            
            # Find historical patterns (before current time, with lookback limit)
            lookback_start = max(0, pred_idx - max_lookback)
            historical_end = pred_idx - (gap_days // pattern_window + 1)  # Ensure gap
            
            if historical_end <= lookback_start:
                continue
            
            # Get historical patterns
            historical_patterns = valid_patterns[lookback_start:historical_end]
            historical_indices = valid_indices[lookback_start:historical_end]
            
            if len(historical_patterns) < top_k_patterns:
                continue
            
            # VECTORIZED: Compute all distances at once
            distances = cdist([current_pattern_norm], historical_patterns, metric='euclidean')[0]
            
            # Get top-k most similar
            top_k_idx = np.argpartition(distances, min(top_k_patterns, len(distances)-1))[:top_k_patterns]
            similar_indices = historical_indices[top_k_idx]
            
            # Calculate returns for similar patterns
            future_returns = (close_prices[similar_indices + gap_days] - close_prices[similar_indices]) / close_prices[similar_indices]
            
            # Average expected return
            avg_expected_return = np.mean(future_returns)
            current_price = close_prices[i]
            expected_price = current_price * (1 + avg_expected_return)
            
            # Actual return
            actual_price_after_gap = close_prices[i + gap_days]
            actual_return = (actual_price_after_gap - current_price) / current_price
            
            # Success flag
            if abs(avg_expected_return) >= price_change_threshold:
                same_direction = (avg_expected_return * actual_return) > 0
                magnitude_met = abs(actual_return) >= price_change_threshold
                success = same_direction and magnitude_met
            else:
                success = abs(actual_return) < price_change_threshold
            
            # Max return within gap
            future_prices = close_prices[i+1:i+gap_days+1]
            max_return = (np.max(future_prices) - current_price) / current_price
            
            # Store results
            expected_prices[pred_idx] = expected_price
            predicted_returns[pred_idx] = avg_expected_return
            actual_returns[pred_idx] = actual_return
            success_flags[pred_idx] = success
            max_returns_within_gap[pred_idx] = max_return
        
        # Pad with NaN
        pad_start = [np.nan] * pattern_window
        pad_end = [np.nan] * gap_days
        
        df_predictions[f'expected_price_{indicator}'] = pad_start + list(expected_prices) + pad_end
        df_predictions[f'predicted_return_{indicator}'] = pad_start + list(predicted_returns) + pad_end
        df_predictions[f'actual_return_{indicator}'] = pad_start + list(actual_returns) + pad_end
        
        # Calculate summary statistics
        valid_mask = ~np.isnan(success_flags)
        
        if np.sum(valid_mask) > 0:
            probability_of_success = np.mean(success_flags[valid_mask])
            avg_max_return = np.mean(max_returns_within_gap[valid_mask])
            avg_predicted_return = np.mean(predicted_returns[valid_mask])
            avg_actual_return = np.mean(actual_returns[valid_mask])
            
            # Additional metrics
            valid_predicted = predicted_returns[valid_mask]
            valid_actual = actual_returns[valid_mask]
            
            profitable_predictions = np.sum((valid_predicted > 0) & (valid_actual > 0))
            total_predictions = len(valid_predicted)
            directional_accuracy = profitable_predictions / total_predictions if total_predictions > 0 else 0
            
            # Sharpe-like ratio
            if np.std(valid_actual) > 0:
                return_to_volatility = avg_actual_return / np.std(valid_actual)
            else:
                return_to_volatility = 0
            
            summary[indicator] = {
                'probability_of_success': probability_of_success,
                'avg_max_return': avg_max_return,
                'avg_predicted_return': avg_predicted_return,
                'avg_actual_return': avg_actual_return,
                'directional_accuracy': directional_accuracy,
                'return_to_volatility_ratio': return_to_volatility,
                'num_predictions': int(np.sum(valid_mask)),
                'num_successful': int(np.sum(success_flags[valid_mask]))
            }
            
            if log:
                logger.info(f"  {indicator} Summary:")
                logger.info(f"    Success Rate: {probability_of_success:.2%}")
                logger.info(f"    Avg Max Return: {avg_max_return:.2%}")
                logger.info(f"    Directional Accuracy: {directional_accuracy:.2%}")
                logger.info(f"    Total Predictions: {int(np.sum(valid_mask))}")
        else:
            summary[indicator] = {
                'probability_of_success': np.nan,
                'avg_max_return': np.nan,
                'avg_predicted_return': np.nan,
                'avg_actual_return': np.nan,
                'directional_accuracy': np.nan,
                'return_to_volatility_ratio': np.nan,
                'num_predictions': 0,
                'num_successful': 0
            }
            
            if log:
                logger.warning(f"  {indicator}: No valid predictions generated")
    
    # Calculate cumulative expected price
    expected_price_cols = [col for col in df_predictions.columns if col.startswith('expected_price_')]
    if expected_price_cols:
        df_predictions['expected_price_cumulative'] = df_predictions[expected_price_cols].mean(axis=1)
        if log:
            logger.info(f"Calculated cumulative expected price from {len(expected_price_cols)} indicators")
    
    if log:
        logger.info("Indicator effectiveness calculation completed")
    
    return df_predictions, summary






prices_dir = "database/historical_data_yf"
stock_code = "TCS"


def load_data(stock):
    file_path = f"{prices_dir}/{stock}.NS_yf.json"
    df = pd.read_json(file_path).T
    
    dates = pd.to_datetime(df.index.tolist()).tolist()
    
    cols = df.columns.tolist()
    cols = [c.replace(f"_{stock}.NS", '').lower() for c in cols]
    df.columns = cols
    return df, dates, cols


logger.info(f"Loading data for {stock_code} from {prices_dir}")
df, dates, cols = load_data(stock_code)

logger.info(f"Loaded data for {stock_code}: {len(df)} rows")



logger.info(f"Starting indicator addition")
df = add_indicators(df)
logger.info(f"Primary indicators added")



# Usage example:
indicators_to_test = ['rsi', 'macd', 'obv', 'atr', 'stoch_k']
indicators_to_test = ['rsi']

df_pred, summary = calculate_indicator_effectiveness(
    df=df,
    indicators=indicators_to_test,
    gap_days=5,
    price_change_threshold=0.02,  # 2% threshold
    pattern_window=10,
    top_k_patterns=5,
    log=True,
)

# View summary
import pprint
pprint.pprint(summary)

# View predictions
# print(df_pred[['close', 'expected_price_rsi', 'expected_price_macd', 'expected_price_cumulative']].tail(20))
print(df_pred.tail())


