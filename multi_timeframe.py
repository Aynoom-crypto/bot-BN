import pandas as pd
import numpy as np
import ta

class MultiTimeframeAnalyzer:
    def __init__(self, config):
        self.config = config
        
    def calculate_indicators(self, df):
        """คำนวณ indicators สำหรับ timeframe หนึ่ง"""
        if df.empty or len(df) < 50:
            return None
            
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=self.config.RSI_PERIOD).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'], 
                            window_slow=self.config.MACD_SLOW,
                            window_fast=self.config.MACD_FAST,
                            window_sign=self.config.MACD_SIGNAL)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], 
                                         window=self.config.BB_PERIOD,
                                         window_dev=self.config.BB_STD)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price position in BB
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    def analyze_all_timeframes(self, symbol, client):
        """วิเคราะห์ข้อมูลทุก timeframe"""
        timeframe_signals = {}
        
        for tf in self.config.TIMEFRAMES:
            try:
                # ดึงข้อมูล candles
                klines = client.get_klines(symbol=symbol, interval=tf, limit=100)
                
                if not klines:
                    continue
                    
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
                ])
                
                # Convert to numeric
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
                
                # Calculate indicators
                df = self.calculate_indicators(df)
                
                if df is not None:
                    latest = df.iloc[-1]
                    timeframe_signals[tf] = {
                        'close': latest['close'],
                        'rsi': latest['rsi'],
                        'macd': latest['macd'],
                        'macd_signal': latest['macd_signal'],
                        'macd_diff': latest['macd_diff'],
                        'bb_position': latest['bb_position'],
                        'bb_width': latest['bb_width'],
                        'volume_ratio': latest['volume_ratio']
                    }
                    
            except Exception as e:
                print(f"Error analyzing {symbol} on {tf}: {e}")
                continue
                
        return timeframe_signals
