#!/usr/bin/env python3
"""
ENHANCED CRYPTRO BOT
เทรดทุกเหรียญบน Binance
- ใช้เงินทั้งหมดเมื่อเข้าเงื่อนไข
- ตั้ง TP ล่วงหน้า 6%
- ไม่มี Stop Loss
- วิเคราะห์ Multi-timeframe (M5 ถึง 1D)
- มี Risk Management
- Logging ละเอียด
- Telegram Notifications
- รันบน Termux
"""

# ============================================
# IMPORTS
# ============================================

import os
import sys
import json
import time
import schedule
import requests
import logging
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal, ROUND_DOWN

# Third-party imports
try:
    from binance.client import Client
    from binance.enums import *
    from binance.exceptions import BinanceAPIException
    import pandas as pd
    import numpy as np
    import ta
    from colorama import init, Fore, Style, Back
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install requirements: pip install python-binance pandas numpy ta python-dotenv colorama schedule requests")
    sys.exit(1)

# Initialize colorama
init(autoreset=True)

# ============================================
# CONFIGURATION
# ============================================

load_dotenv()

class Config:
    """Configuration class for Cryptro Bot"""
    
    # Binance API
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    USE_TESTNET = os.getenv('USE_TESTNET', 'false').lower() == 'true'
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Trading Parameters
    TARGET_PROFIT_PERCENT = 6.0
    USE_ALL_BALANCE = True
    MIN_BALANCE_USDT = 11.0
    MAX_OPEN_POSITIONS = 10
    CHECK_INTERVAL_MINUTES = 5
    
    # Timeframes
    TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d']
    
    # Indicators
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2.0
    
    # Risk Management
    MAX_DAILY_LOSS_PERCENT = -5.0
    MAX_CONSECUTIVE_LOSSES = 3
    MAX_POSITIONS_PER_CATEGORY = 2
    VOLATILITY_THRESHOLD = 0.15
    HIGH_RISK_HOURS = [0, 1, 2, 3, 12, 13, 20, 21]  # UTC
    
    # Logging
    LOG_TO_FILE = True
    LOG_LEVEL = 'INFO'
    LOG_RETENTION_DAYS = 7
    
    # Notifications
    ENABLE_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    NOTIFY_ON_SIGNAL = True
    NOTIFY_ON_EXECUTION = True
    NOTIFY_ON_RESULT = True
    NOTIFY_DAILY_REPORT = True
    NOTIFY_ERRORS = True
    DAILY_REPORT_HOUR = 0  # UTC
    
    # Other
    BLACKLIST = []
    VERSION = "2.0.0"
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
            raise ValueError("Binance API keys must be set in .env file")
        print(f"✓ Configuration validated - Version {cls.VERSION}")

# ============================================
# DATA MODELS
# ============================================

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Signal:
    """Trade signal data model"""
    symbol: str
    signal_type: SignalType
    score: int
    price: float
    take_profit: float
    conditions: List[str]
    timestamp: datetime
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'signal': self.signal_type.value,
            'score': self.score,
            'price': self.price,
            'take_profit': self.take_profit,
            'conditions': self.conditions,
            'timestamp': self.timestamp.isoformat(),
            'target_percent': Config.TARGET_PROFIT_PERCENT
        }

@dataclass
class Position:
    """Open position data model"""
    symbol: str
    quantity: float
    entry_price: float
    take_profit: float
    tp_order_id: str
    entry_time: datetime
    
    def to_dict(self):
        return asdict(self)

@dataclass 
class TradeResult:
    """Trade result data model"""
    symbol: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl_percent: float
    pnl_amount: float
    duration: str
    result_type: str  # 'profit' or 'loss'
    timestamp: datetime

# ============================================
# ENHANCED LOGGER
# ============================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        return super().format(record)

class EnhancedLogger:
    """Enhanced logging system with file logging and trade tracking"""
    
    def __init__(self, name="CryptroBot", log_to_file=True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handlers if enabled
        if log_to_file:
            self._setup_file_handlers()
        
        # Trade history
        self.trade_history = []
        
        # Ensure logs directory exists
        if log_to_file and not os.path.exists('logs'):
            os.makedirs('logs')
    
    def _setup_file_handlers(self):
        """Setup file handlers for different log types"""
        
        # Main log file
        main_handler = logging.FileHandler('logs/cryptro_bot.log')
        main_handler.setLevel(logging.DEBUG)
        main_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        self.logger.addHandler(main_handler)
        
        # Error log file
        error_handler = logging.FileHandler('logs/cryptro_errors.log')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(main_formatter)
        self.logger.addHandler(error_handler)
        
        # Trade log file
        trade_handler = logging.FileHandler('logs/cryptro_trades.log')
        trade_handler.setLevel(logging.INFO)
        trade_formatter = logging.Formatter('%(asctime)s - TRADE - %(message)s')
        trade_handler.setFormatter(trade_formatter)
        self.logger.addHandler(trade_handler)
    
    # Logging methods
    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)
    
    def trade_signal(self, signal: Signal):
        """Log a trade signal"""
        signal_dict = signal.to_dict()
        self.info(f"""
{'='*60}
TRADE SIGNAL DETECTED
Symbol: {signal.symbol}
Signal: {signal.signal_type.value}
Score: {signal.score}/100
Price: ${signal.price:.8f}
Take Profit: ${signal.take_profit:.8f} (+{Config.TARGET_PROFIT_PERCENT}%)
Conditions: {', '.join(signal.conditions)}
Timestamp: {signal.timestamp}
{'='*60}
        """)
        self._save_trade_log('signal', signal_dict)
    
    def trade_execution(self, order_type: str, symbol: str, details: Dict):
        """Log trade execution"""
        self.info(f"""
{'-'*40}
ORDER EXECUTED
Type: {order_type}
Symbol: {symbol}
Details: {json.dumps(details, indent=2, default=str)}
Time: {datetime.now()}
{'-'*40}
        """)
        self._save_trade_log('execution', {
            'order_type': order_type,
            'symbol': symbol,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def trade_result(self, result: TradeResult):
        """Log trade result"""
        color = Fore.GREEN if result.result_type == 'profit' else Fore.RED
        self.info(f"""
{color}{'*'*40}
TRADE RESULT: {result.result_type.upper()}
Symbol: {result.symbol}
P&L: {result.pnl_percent:+.2f}%
Amount: ${result.pnl_amount:+.2f}
Duration: {result.duration}
Time: {result.timestamp}
{'*'*40}{Style.RESET_ALL}
        """)
        self._save_trade_log('result', asdict(result))
    
    def performance_report(self, report_data: Dict):
        """Log performance report"""
        self.info(f"""
{Back.CYAN}{Fore.BLACK}{'='*60}
PERFORMANCE REPORT
{'='*60}{Style.RESET_ALL}
Total Trades: {report_data.get('total_trades', 0)}
Win Rate: {report_data.get('win_rate', 0):.1f}%
Total P&L: {report_data.get('total_pnl', 0):.2f}%
Daily P&L: {report_data.get('daily_pnl', 0):.2f}%
Best Trade: {report_data.get('best_trade', 0):.2f}%
Worst Trade: {report_data.get('worst_trade', 0):.2f}%
Open Positions: {report_data.get('open_positions', 0)}
Account Balance: ${report_data.get('account_balance', 0):.2f}
{'='*60}
        """)
    
    def _save_trade_log(self, log_type: str, data: Dict):
        """Save trade log to JSON file"""
        try:
            log_file = 'logs/trade_history.json'
            record = {'type': log_type, 'timestamp': datetime.now().isoformat(), 'data': data}
            
            # Load existing data
            existing_data = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = []
            
            # Append new record and keep only last 1000
            existing_data.append(record)
            if len(existing_data) > 1000:
                existing_data = existing_data[-1000:]
            
            # Save back to file
            with open(log_file, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)
                
        except Exception as e:
            self.error(f"Error saving trade log: {e}")
    
    def cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=Config.LOG_RETENTION_DAYS)
            
            for filename in os.listdir('logs'):
                if filename.endswith('.log'):
                    filepath = os.path.join('logs', filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        self.debug(f"Cleaned up old log: {filename}")
            
            # Clean trade history JSON
            log_file = 'logs/trade_history.json'
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    data = json.load(f)
                
                filtered_data = []
                for record in data:
                    record_time = datetime.fromisoformat(record.get('timestamp', '2020-01-01'))
                    if record_time > cutoff_date:
                        filtered_data.append(record)
                
                with open(log_file, 'w') as f:
                    json.dump(filtered_data, f, indent=2, default=str)
                
                self.debug("Cleaned up old trade history records")
                
        except Exception as e:
            self.error(f"Error cleaning up logs: {e}")

# ============================================
# TELEGRAM NOTIFIER
# ============================================

class TelegramNotifier:
    """Telegram notification system"""
    
    def __init__(self, bot_token: str, chat_id: str, logger: EnhancedLogger):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.logger = logger
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Message queue for rate limiting
        self.message_queue = []
        self._last_sent = 0
        self.sending = False
        
        # Test connection
        if self._test_connection():
            self.start_message_sender()
    
    def _test_connection(self) -> bool:
        """Test Telegram connection"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                self.logger.info("✓ Telegram connection successful")
                return True
            else:
                self.logger.error(f"Telegram connection failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Telegram connection error: {e}")
            return False
    
    def send_message(self, text: str, parse_mode='HTML', disable_notification=False):
        """Add message to queue for sending"""
        self.message_queue.append({
            'text': text,
            'parse_mode': parse_mode,
            'disable_notification': disable_notification,
            'timestamp': time.time()
        })
    
    def send_immediate(self, text: str, parse_mode='HTML') -> bool:
        """Send message immediately (for important alerts)"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"Telegram send failed: {response.text}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def start_message_sender(self):
        """Start background thread for sending messages with rate limiting"""
        def sender_thread():
            while True:
                try:
                    if self.message_queue:
                        message = self.message_queue.pop(0)
                        
                        # Rate limiting (30 messages/second)
                        current_time = time.time()
                        time_since_last = current_time - self._last_sent
                        
                        if time_since_last < 0.034:
                            time.sleep(0.034 - time_since_last)
                        
                        # Send message
                        payload = {
                            'chat_id': self.chat_id,
                            'text': message['text'],
                            'parse_mode': message['parse_mode'],
                            'disable_notification': message['disable_notification'],
                            'disable_web_page_preview': True
                        }
                        
                        response = requests.post(
                            f"{self.base_url}/sendMessage",
                            json=payload,
                            timeout=10
                        )
                        
                        self._last_sent = time.time()
                        
                        if response.status_code != 200:
                            self.logger.error(f"Failed to send queued message: {response.text}")
                            # Retry
                            self.message_queue.insert(0, message)
                            time.sleep(1)
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Telegram sender thread error: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=sender_thread, daemon=True)
        thread.start()
        self.sending = True
        self.logger.debug("Telegram message sender started")
    
    # Notification methods
    def notify_signal(self, signal: Signal):
        """Notify about trade signal"""
        emoji = "🚀" if signal.signal_type == SignalType.BUY else "🔻"
        text = f"""
{emoji} <b>TRADE SIGNAL DETECTED</b> {emoji}

<b>Symbol:</b> {signal.symbol}
<b>Signal:</b> {signal.signal_type.value}
<b>Score:</b> {signal.score}/100
<b>Price:</b> ${signal.price:.8f}
<b>Take Profit:</b> ${signal.take_profit:.8f} (+{Config.TARGET_PROFIT_PERCENT:.1f}%)

<b>Conditions:</b>
{chr(10).join(['• ' + cond for cond in signal.conditions])}

<b>Time:</b> {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        self.send_message(text)
    
    def notify_order_execution(self, order_type: str, symbol: str, details: Dict):
        """Notify about order execution"""
        emoji = "🟢" if order_type == 'BUY' else "🔴"
        text = f"""
{emoji} <b>ORDER EXECUTED</b> {emoji}

<b>Type:</b> {order_type}
<b>Symbol:</b> {symbol}

<b>Details:</b>
• Quantity: {details.get('quantity', 'N/A')}
• Price: ${details.get('price', 'N/A'):.8f}
• Total: ${details.get('total', 'N/A'):.2f}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        self.send_immediate(text)
    
    def notify_trade_result(self, result: TradeResult):
        """Notify about trade result"""
        if result.result_type == 'profit':
            emoji = "💰"
            title = "TAKE PROFIT HIT"
        else:
            emoji = "💸"
            title = "STOP LOSS HIT"
        
        pnl_color = "🟢" if result.pnl_percent > 0 else "🔴"
        
        text = f"""
{emoji} <b>{title}</b> {emoji}

<b>Symbol:</b> {result.symbol}
<b>P&L:</b> {pnl_color} {result.pnl_percent:+.2f}%

<b>Details:</b>
• Entry: ${result.entry_price:.8f}
• Exit: ${result.exit_price:.8f}
• Duration: {result.duration}
• Quantity: {result.quantity}

<b>Total Profit:</b> ${result.pnl_amount:.2f}
<b>Time:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        self.send_message(text)
    
    def notify_daily_report(self, report_data: Dict):
        """Notify daily report"""
        daily_pnl = report_data.get('daily_pnl', 0)
        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
        
        text = f"""
{pnl_emoji} <b>DAILY TRADING REPORT</b> {pnl_emoji}

<b>Daily P&L:</b> {daily_pnl:+.2f}%
<b>Total Trades:</b> {report_data.get('total_trades', 0)}
<b>Win Rate:</b> {report_data.get('win_rate', 0):.1f}%

<b>Performance:</b>
• Best Trade: {report_data.get('best_trade', 0):+.2f}%
• Worst Trade: {report_data.get('worst_trade', 0):+.2f}%
• Avg Win: {report_data.get('avg_win', 0):.2f}%
• Avg Loss: {report_data.get('avg_loss', 0):.2f}%

<b>Current Status:</b>
• Open Positions: {report_data.get('open_positions', 0)}
• Account Balance: ${report_data.get('account_balance', 0):.2f}
• Available: ${report_data.get('available_balance', 0):.2f}

<b>Report Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        self.send_message(text)
    
    def notify_error(self, error_message: str, context: str = ""):
        """Notify about error"""
        text = f"""
🚨 <b>BOT ERROR</b> 🚨

<b>Error:</b> {error_message}

<b>Context:</b>
{context}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

<i>Please check the bot immediately!</i>
        """
        self.send_immediate(text)
    
    def notify_bot_status(self, status: str, uptime: str = "", version: str = ""):
        """Notify bot status"""
        emoji = "✅" if status == "started" else "🛑"
        text = f"""
{emoji} <b>BOT STATUS UPDATE</b> {emoji}

<b>Status:</b> {status.upper()}
<b>Uptime:</b> {uptime}
<b>Version:</b> {version}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        self.send_message(text)

# ============================================
# RISK MANAGEMENT
# ============================================

class RiskManager:
    """Risk management system"""
    
    def __init__(self, logger: EnhancedLogger):
        self.logger = logger
        
        # Risk metrics
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.trade_history = []
        
        # Risk parameters
        self.max_daily_loss = Config.MAX_DAILY_LOSS_PERCENT
        self.max_consecutive_losses = Config.MAX_CONSECUTIVE_LOSSES
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit reached"""
        if self.daily_pnl <= self.max_daily_loss:
            self.logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f}%")
            return False
        return True
    
    def check_consecutive_losses(self) -> bool:
        """Check if max consecutive losses reached"""
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.warning(f"Max consecutive losses reached: {self.consecutive_losses}")
            return False
        return True
    
    def check_market_volatility(self, symbol: str, timeframe_data: Dict) -> bool:
        """Check market volatility risk"""
        volatility_score = 0
        
        for tf, data in timeframe_data.items():
            if 'bb_width' in data:
                bb_width = data['bb_width']
                if bb_width > 0.15:  # High volatility
                    volatility_score += 2
                elif bb_width < 0.03:  # Too low volatility
                    volatility_score += 1
        
        if volatility_score >= 4:
            self.logger.warning(f"High volatility risk for {symbol}")
            return False
        
        return True
    
    def check_correlation_risk(self, symbol: str, open_positions: Dict) -> bool:
        """Check correlation risk with existing positions"""
        if len(open_positions) == 0:
            return True
        
        symbol_base = symbol.replace('USDT', '').lower()
        similar_coins = 0
        
        # Simple category check
        categories = {
            'layer2': ['matic', 'arb', 'op', 'imx'],
            'ai': ['agix', 'fet', 'ocean', 'rndr'],
            'meme': ['doge', 'shib', 'pepe', 'floki'],
            'defi': ['uni', 'aave', 'comp', 'mkr'],
        }
        
        for pos_symbol in open_positions.keys():
            pos_base = pos_symbol.replace('USDT', '').lower()
            
            for category, coins in categories.items():
                if symbol_base in coins and pos_base in coins:
                    similar_coins += 1
                    break
        
        if similar_coins >= Config.MAX_POSITIONS_PER_CATEGORY:
            self.logger.warning(f"Correlation risk for {symbol}: {similar_coins} similar coins")
            return False
        
        return True
    
    def check_time_based_risk(self) -> float:
        """Check time-based risk and return position size factor"""
        hour = datetime.utcnow().hour
        
        if hour in Config.HIGH_RISK_HOURS:
            self.logger.warning(f"High risk trading hour: {hour}:00 UTC")
            return 0.5  # Reduce position size by 50%
        
        return 1.0
    
    def check_volume_risk(self, symbol: str, timeframe_data: Dict) -> bool:
        """Check volume risk"""
        for tf, data in timeframe_data.items():
            if 'volume_ratio' in data and tf in ['1h', '4h', '1d']:
                if data['volume_ratio'] < 0.5:
                    self.logger.warning(f"Low volume risk for {symbol} on {tf}")
                    return False
        return True
    
    def update_trade_result(self, symbol: str, pnl_percent: float, is_win: bool):
        """Update trade result in risk metrics"""
        self.daily_pnl += pnl_percent
        self.daily_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Add to history
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'pnl_percent': pnl_percent,
            'is_win': is_win
        })
        
        # Keep only last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
    
    def get_risk_report(self) -> str:
        """Generate risk report"""
        if not self.trade_history:
            return "No trade history yet"
        
        recent_trades = self.trade_history[-20:]
        wins = sum(1 for trade in recent_trades if trade['is_win'])
        losses = len(recent_trades) - wins
        win_rate = (wins / len(recent_trades) * 100) if recent_trades else 0
        
        total_pnl = sum(trade['pnl_percent'] for trade in recent_trades)
        avg_win = np.mean([t['pnl_percent'] for t in recent_trades if t['is_win']]) if wins > 0 else 0
        avg_loss = np.mean([t['pnl_percent'] for t in recent_trades if not t['is_win']]) if losses > 0 else 0
        
        return f"""
=== RISK MANAGEMENT REPORT ===
Daily P&L: {self.daily_pnl:.2f}%
Daily Trades: {self.daily_trades}
Consecutive Losses: {self.consecutive_losses}

Recent Performance (Last 20 trades):
Win Rate: {win_rate:.1f}%
Total P&L: {total_pnl:.2f}%
Average Win: {avg_win:.2f}%
Average Loss: {avg_loss:.2f}%
Profit Factor: {abs(avg_win/avg_loss):.2f if avg_loss != 0 else 'N/A'}
==============================
        """
    
    def reset_daily_metrics(self):
        """Reset daily metrics at midnight UTC"""
        now = datetime.utcnow()
        if now.hour == 0 and now.minute < 5:
            self.daily_pnl = 0
            self.daily_trades = 0
            self.logger.info("Daily risk metrics reset")

# ============================================
# BINANCE CLIENT
# ============================================

class BinanceClient:
    """Binance API client wrapper"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(api_key, api_secret)
        
        if Config.USE_TESTNET:
            self.client.API_URL = 'https://testnet.binance.vision/api'
            print("⚠️  Using Binance TESTNET")
        
        self.logger = EnhancedLogger("BinanceClient")
    
    def get_account_balance(self) -> Dict:
        """Get account balance"""
        try:
            account = self.client.get_account()
            balances = {}
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting balance: {e}")
            return {}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List:
        """Get klines/candlestick data"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return klines
        except Exception as e:
            self.logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def get_all_trading_pairs(self, quote_asset: str = 'USDT') -> List[str]:
        """Get all trading pairs for quote asset"""
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                
                if (symbol.endswith(quote_asset) and 
                    symbol_info['status'] == 'TRADING' and
                    not any(x in symbol for x in ['UP', 'DOWN', 'BEAR', 'BULL'])):
                    
                    symbols.append(symbol)
            
            return symbols
            
        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {e}")
            return []
    
    def place_market_order(self, symbol: str, side: str, quantity: float):
        """Place market order"""
        try:
            # Get symbol info for precision
            symbol_info = self.client.get_symbol_info(symbol)
            filters = {f['filterType']: f for f in symbol_info['filters']}
            
            # Adjust quantity to lot size
            if 'LOT_SIZE' in filters:
                step_size = float(filters['LOT_SIZE']['stepSize'])
                precision = int(round(-np.log10(step_size)))
                quantity = round(int(quantity / step_size) * step_size, precision)
            
            # Place order
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing market order for {symbol}: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float):
        """Place limit order"""
        try:
            # Get symbol info
            symbol_info = self.client.get_symbol_info(symbol)
            filters = {f['filterType']: f for f in symbol_info['filters']}
            
            # Adjust quantity
            if 'LOT_SIZE' in filters:
                step_size = float(filters['LOT_SIZE']['stepSize'])
                precision = int(round(-np.log10(step_size)))
                quantity = round(int(quantity / step_size) * step_size, precision)
            
            # Adjust price
            if 'PRICE_FILTER' in filters:
                tick_size = float(filters['PRICE_FILTER']['tickSize'])
                price_precision = int(round(-np.log10(tick_size)))
                price = round(price, price_precision)
            
            # Place order
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing limit order for {symbol}: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            return True
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    def get_open_orders(self, symbol: str = None) -> List:
        """Get open orders"""
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            return self.client.get_open_orders()
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return []
    
    def get_symbol_ticker(self, symbol: str) -> Dict:
        """Get symbol ticker price"""
        try:
            return self.client.get_symbol_ticker(symbol=symbol)
        except Exception as e:
            self.logger.error(f"Error getting ticker for {symbol}: {e}")
            return {'price': '0'}

# ============================================
# TECHNICAL ANALYSIS
# ============================================

class TechnicalAnalyzer:
    """Technical analysis with multi-timeframe support"""
    
    def __init__(self):
        pass
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators on dataframe"""
        if df.empty or len(df) < 50:
            return df
        
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(
            df['close'], 
            window=Config.RSI_PERIOD
        ).rsi()
        
        # MACD
        macd = ta.trend.MACD(
            df['close'],
            window_slow=Config.MACD_SLOW,
            window_fast=Config.MACD_FAST,
            window_sign=Config.MACD_SIGNAL
        )
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(
            df['close'],
            window=Config.BB_PERIOD,
            window_dev=Config.BB_STD
        )
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma'].replace(0, 1)
        
        # BB Position
        df['bb_position'] = (df['close'] - df['bb_lower']) / (
            df['bb_upper'] - df['bb_lower']
        ).replace(0, 1)
        
        return df
    
    def analyze_timeframe(self, client: BinanceClient, symbol: str, timeframe: str) -> Dict:
        """Analyze single timeframe"""
        try:
            klines = client.get_klines(symbol, timeframe, 100)
            
            if not klines:
                return {}
            
            # Create DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert to numeric
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            if df.empty or df['close'].isna().iloc[-1]:
                return {}
            
            latest = df.iloc[-1]
            
            return {
                'close': float(latest['close']),
                'rsi': float(latest['rsi']),
                'macd': float(latest['macd']),
                'macd_signal': float(latest['macd_signal']),
                'macd_diff': float(latest['macd_diff']),
                'bb_position': float(latest['bb_position']),
                'bb_width': float(latest['bb_width']),
                'volume_ratio': float(latest['volume_ratio'])
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol} on {timeframe}: {e}")
            return {}
    
    def analyze_all_timeframes(self, client: BinanceClient, symbol: str) -> Dict:
        """Analyze all configured timeframes"""
        results = {}
        
        for tf in Config.TIMEFRAMES:
            data = self.analyze_timeframe(client, symbol, tf)
            if data:
                results[tf] = data
        
        return results

# ============================================
# SIGNAL GENERATOR
# ============================================

class SignalGenerator:
    """Generate trading signals from technical analysis"""
    
    def __init__(self):
        pass
    
    def generate_signal(self, symbol: str, timeframe_data: Dict) -> Optional[Signal]:
        """Generate trading signal from multi-timeframe data"""
        if not timeframe_data:
            return None
        
        # Check required timeframes
        required_tfs = ['5m', '15m', '1h', '4h']
        if not all(tf in timeframe_data for tf in required_tfs):
            return None
        
        signal_score = 0
        conditions_met = []
        
        # 1. Multi-timeframe trend alignment
        bullish_tfs = 0
        bearish_tfs = 0
        
        for tf, data in timeframe_data.items():
            tf_bullish = 0
            tf_bearish = 0
            
            # RSI
            if data['rsi'] < 35:
                tf_bullish += 1
            elif data['rsi'] > 65:
                tf_bearish += 1
            
            # MACD
            if data['macd_diff'] > 0:
                tf_bullish += 1
            elif data['macd_diff'] < 0:
                tf_bearish += 1
            
            # Bollinger Band position
            if data['bb_position'] < 0.2:
                tf_bullish += 1
            elif data['bb_position'] > 0.8:
                tf_bearish += 1
            
            # Volume
            if data['volume_ratio'] > 1.2:
                if tf_bullish > tf_bearish:
                    tf_bullish += 1
                elif tf_bearish > tf_bullish:
                    tf_bearish += 1
            
            if tf_bullish > tf_bearish:
                bullish_tfs += 1
            elif tf_bearish > tf_bullish:
                bearish_tfs += 1
        
        if bullish_tfs >= 3:
            signal_score += 30
            conditions_met.append("multi_tf_bullish")
        
        # 2. Short-term momentum
        short_term_bullish = True
        for tf in ['5m', '15m']:
            if tf in timeframe_data:
                data = timeframe_data[tf]
                if data['macd_diff'] <= 0 or data['rsi'] < 45:
                    short_term_bullish = False
                    break
        
        if short_term_bullish:
            signal_score += 20
            conditions_met.append("short_term_momentum")
        
        # 3. Medium-term trend
        medium_term_bullish = True
        for tf in ['1h', '4h']:
            if tf in timeframe_data:
                data = timeframe_data[tf]
                if data['macd'] < data['macd_signal']:
                    medium_term_bullish = False
                    break
        
        if medium_term_bullish:
            signal_score += 25
            conditions_met.append("medium_term_trend")
        
        # 4. Daily confirmation
        if '1d' in timeframe_data:
            data = timeframe_data['1d']
            if data['macd_diff'] > 0:
                signal_score += 15
                conditions_met.append("daily_confirmation")
        
        # 5. Check volatility
        low_volatility = all(
            data['bb_width'] < 0.1 
            for tf, data in timeframe_data.items() 
            if 'bb_width' in data
        )
        
        if low_volatility:
            signal_score -= 10
        
        # Generate signal if conditions met
        if signal_score >= 60 and len(conditions_met) >= 3:
            current_price = timeframe_data['5m']['close']
            
            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                score=signal_score,
                price=current_price,
                take_profit=current_price * (1 + Config.TARGET_PROFIT_PERCENT / 100),
                conditions=conditions_met,
                timestamp=datetime.now()
            )
        
        return None

# ============================================
# ORDER MANAGER
# ============================================

class OrderManager:
    """Manage trading orders and positions"""
    
    def __init__(self, client: BinanceClient, logger: EnhancedLogger):
        self.client = client
        self.logger = logger
        self.open_positions = {}  # symbol -> Position
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                                risk_factor: float = 1.0) -> float:
        """Calculate position size based on risk management"""
        try:
            balances = self.client.get_account_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            if usdt_balance < Config.MIN_BALANCE_USDT:
                self.logger.warning(f"Insufficient balance: {usdt_balance:.2f} USDT")
                return 0
            
            # Calculate base position size
            if Config.USE_ALL_BALANCE:
                available = usdt_balance * 0.999  # Account for fees
            else:
                available = usdt_balance / Config.MAX_OPEN_POSITIONS
            
            # Apply risk factor
            risk_adjusted = available * risk_factor
            
            # Calculate quantity
            quantity = risk_adjusted / entry_price
            
            # Check minimum notional (10 USDT for Binance)
            notional = quantity * entry_price
            if notional < 10:
                self.logger.warning(f"Notional too small: ${notional:.2f}")
                return 0
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0
    
    def execute_buy(self, signal: Signal, risk_factor: float = 1.0) -> bool:
        """Execute buy order based on signal"""
        try:
            symbol = signal.symbol
            
            # Check if already have position
            if symbol in self.open_positions:
                self.logger.warning(f"Already have position for {symbol}")
                return False
            
            # Calculate position size
            quantity = self.calculate_position_size(
                symbol, 
                signal.price, 
                risk_factor
            )
            
            if quantity <= 0:
                self.logger.warning(f"Insufficient position size for {symbol}")
                return False
            
            # Execute market buy
            buy_order = self.client.place_market_order(
                symbol=symbol,
                side=SIDE_BUY,
                quantity=quantity
            )
            
            if not buy_order:
                self.logger.error(f"Buy order failed for {symbol}")
                return False
            
            # Get actual executed price
            executed_price = float(buy_order['fills'][0]['price'])
            
            # Place take profit limit order
            tp_order = self.client.place_limit_order(
                symbol=symbol,
                side=SIDE_SELL,
                quantity=quantity,
                price=signal.take_profit
            )
            
            if not tp_order:
                self.logger.error(f"Take profit order failed for {symbol}")
                # Try to sell immediately
                self.client.place_market_order(symbol, SIDE_SELL, quantity)
                return False
            
            # Record position
            self.open_positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=executed_price,
                take_profit=signal.take_profit,
                tp_order_id=tp_order['orderId'],
                entry_time=datetime.now()
            )
            
            self.logger.info(f"""
✅ Position opened: {symbol}
Quantity: {quantity:.4f}
Entry: ${executed_price:.8f}
Take Profit: ${signal.take_profit:.8f}
Target: +{Config.TARGET_PROFIT_PERCENT:.1f}%
            """)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing buy for {signal.symbol}: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def close_position(self, symbol: str, reason: str = "manual") -> Optional[TradeResult]:
        """Close a position manually"""
        try:
            if symbol not in self.open_positions:
                self.logger.warning(f"No position found for {symbol}")
                return None
            
            position = self.open_positions[symbol]
            
            # Cancel TP order
            self.client.cancel_order(symbol, position.tp_order_id)
            
            # Market sell
            sell_order = self.client.place_market_order(
                symbol=symbol,
                side=SIDE_SELL,
                quantity=position.quantity
            )
            
            if not sell_order:
                self.logger.error(f"Sell order failed for {symbol}")
                return None
            
            # Calculate P&L
            exit_price = float(sell_order['fills'][0]['price'])
            pnl_percent = ((exit_price - position.entry_price) / position.entry_price) * 100
            pnl_amount = (exit_price - position.entry_price) * position.quantity
            duration = str(datetime.now() - position.entry_time)
            
            result = TradeResult(
                symbol=symbol,
                entry_price=position.entry_price,
                exit_price=exit_price,
                quantity=position.quantity,
                pnl_percent=pnl_percent,
                pnl_amount=pnl_amount,
                duration=duration,
                result_type='profit' if pnl_percent > 0 else 'loss',
                timestamp=datetime.now()
            )
            
            # Remove from open positions
            del self.open_positions[symbol]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error closing position {symbol}: {e}")
            return None
    
    def check_open_positions(self, risk_manager: RiskManager, 
                           telegram: Optional[TelegramNotifier] = None) -> List[TradeResult]:
        """Check and update open positions"""
        results = []
        positions_to_remove = []
        
        for symbol, position in list(self.open_positions.items()):
            try:
                # Check if TP order still exists
                open_orders = self.client.get_open_orders(symbol)
                tp_order_exists = any(
                    order['orderId'] == position.tp_order_id 
                    for order in open_orders
                )
                
                if not tp_order_exists:
                    # TP hit or order cancelled
                    positions_to_remove.append((symbol, position))
                    
                    # Get final trade details
                    ticker = self.client.get_symbol_ticker(symbol)
                    exit_price = float(ticker['price'])
                    
                    # Calculate P&L
                    pnl_percent = ((exit_price - position.entry_price) / position.entry_price) * 100
                    pnl_amount = (exit_price - position.entry_price) * position.quantity
                    duration = str(datetime.now() - position.entry_time)
                    
                    result = TradeResult(
                        symbol=symbol,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        quantity=position.quantity,
                        pnl_percent=pnl_percent,
                        pnl_amount=pnl_amount,
                        duration=duration,
                        result_type='profit' if pnl_percent > 0 else 'loss',
                        timestamp=datetime.now()
                    )
                    
                    results.append(result)
                    
                    # Update risk manager
                    risk_manager.update_trade_result(
                        symbol, 
                        pnl_percent, 
                        result.result_type == 'profit'
                    )
                    
                    # Log and notify
                    self.logger.trade_result(result)
                    
                    if telegram and Config.NOTIFY_ON_RESULT:
                        telegram.notify_trade_result(result)
            
            except Exception as e:
                self.logger.error(f"Error checking position {symbol}: {e}")
                continue
        
        # Remove completed positions
        for symbol, _ in positions_to_remove:
            if symbol in self.open_positions:
                del self.open_positions[symbol]
        
        return results

# ============================================
# MAIN BOT CLASS
# ============================================

class CryptroBot:
    """Main Cryptro Bot class"""
    
    def __init__(self):
        # Validate configuration
        Config.validate()
        
        # Initialize components
        self.logger = EnhancedLogger("CryptroBot", Config.LOG_TO_FILE)
        self.client = BinanceClient(Config.BINANCE_API_KEY, Config.BINANCE_API_SECRET)
        self.analyzer = TechnicalAnalyzer()
        self.signal_gen = SignalGenerator()
        self.order_manager = OrderManager(self.client, self.logger)
        self.risk_manager = RiskManager(self.logger)
        
        # Initialize Telegram
        self.telegram = None
        if Config.ENABLE_TELEGRAM:
            try:
                self.telegram = TelegramNotifier(
                    Config.TELEGRAM_BOT_TOKEN,
                    Config.TELEGRAM_CHAT_ID,
                    self.logger
                )
                self.telegram.notify_bot_status("initializing", version=Config.VERSION)
            except Exception as e:
                self.logger.error(f"Failed to initialize Telegram: {e}")
        
        # Bot state
        self.bot_start_time = datetime.now()
        self.is_running = False
        self.blacklist = set(Config.BLACKLIST)
        self.total_trades = 0
        self.winning_trades = 0
        
        self.logger.info(f"✓ Cryptro Bot initialized (v{Config.VERSION})")
    
    def _apply_risk_checks(self, symbol: str, signal: Signal, 
                          timeframe_data: Dict) -> Tuple[bool, float]:
        """Apply all risk management checks"""
        risk_factor = 1.0
        
        # 1. Daily loss limit
        if not self.risk_manager.check_daily_loss_limit():
            self.logger.warning(f"Daily loss limit check failed for {symbol}")
            return False, risk_factor
        
        # 2. Consecutive losses
        if not self.risk_manager.check_consecutive_losses():
            self.logger.warning(f"Consecutive losses check failed for {symbol}")
            return False, risk_factor
        
        # 3. Market volatility
        if not self.risk_manager.check_market_volatility(symbol, timeframe_data):
            self.logger.warning(f"Volatility check failed for {symbol}")
            return False, risk_factor
        
        # 4. Correlation risk
        if not self.risk_manager.check_correlation_risk(symbol, self.order_manager.open_positions):
            self.logger.warning(f"Correlation check failed for {symbol}")
            return False, risk_factor
        
        # 5. Volume risk
        if not self.risk_manager.check_volume_risk(symbol, timeframe_data):
            self.logger.warning(f"Volume check failed for {symbol}")
            return False, risk_factor
        
        # 6. Time-based risk
        risk_factor = self.risk_manager.check_time_based_risk()
        
        return True, risk_factor
    
    def scan_market(self):
        """Scan market for trading opportunities"""
        try:
            self.logger.info("🔍 Starting market scan...")
            
            # Reset daily metrics if needed
            self.risk_manager.reset_daily_metrics()
            
            # Check account balance
            balances = self.client.get_account_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            if usdt_balance < Config.MIN_BALANCE_USDT:
                msg = f"Insufficient balance: {usdt_balance:.2f} USDT"
                self.logger.warning(msg)
                if self.telegram and Config.NOTIFY_ERRORS:
                    self.telegram.notify_error(msg, "Market scan skipped")
                return
            
            # Check open positions
            self.order_manager.check_open_positions(self.risk_manager, self.telegram)
            
            current_positions = len(self.order_manager.open_positions)
            if current_positions >= Config.MAX_OPEN_POSITIONS:
                self.logger.info(f"Max positions reached: {current_positions}")
                return
            
            # Get trading pairs
            symbols = self.client.get_all_trading_pairs('USDT')
            
            # Filter out blacklisted symbols
            symbols_to_scan = [
                s for s in symbols 
                if s not in self.blacklist and s not in self.order_manager.open_positions
            ][:50]  # Limit to avoid rate limits
            
            self.logger.debug(f"Scanning {len(symbols_to_scan)} symbols")
            
            signals_found = 0
            
            for symbol in symbols_to_scan:
                try:
                    # Multi-timeframe analysis
                    timeframe_data = self.analyzer.analyze_all_timeframes(self.client, symbol)
                    
                    if not timeframe_data:
                        continue
                    
                    # Generate signal
                    signal = self.signal_gen.generate_signal(symbol, timeframe_data)
                    
                    if not signal:
                        continue
                    
                    # Apply risk checks
                    risk_ok, risk_factor = self._apply_risk_checks(
                        symbol, signal, timeframe_data
                    )
                    
                    if not risk_ok:
                        continue
                    
                    # Log signal
                    self.logger.trade_signal(signal)
                    
                    # Telegram notification
                    if (self.telegram and 
                        Config.ENABLE_TELEGRAM and 
                        Config.NOTIFY_ON_SIGNAL):
                        self.telegram.notify_signal(signal)
                    
                    # Execute trade
                    success = self.order_manager.execute_buy(signal, risk_factor)
                    
                    if success:
                        signals_found += 1
                        self.total_trades += 1
                        
                        # Add to blacklist temporarily
                        self.blacklist.add(symbol)
                        
                        # Log execution
                        position = self.order_manager.open_positions[symbol]
                        execution_details = {
                            'quantity': position.quantity,
                            'price': position.entry_price,
                            'total': position.quantity * position.entry_price,
                            'take_profit': position.take_profit
                        }
                        self.logger.trade_execution('BUY', symbol, execution_details)
                        
                        # Telegram notification
                        if (self.telegram and 
                            Config.ENABLE_TELEGRAM and 
                            Config.NOTIFY_ON_EXECUTION):
                            self.telegram.notify_order_execution(
                                'BUY', symbol, execution_details
                            )
                        
                        # Rate limiting
                        time.sleep(2)
                    
                except Exception as e:
                    error_msg = f"Error processing {symbol}: {str(e)}"
                    self.logger.error(error_msg)
                    
                    if self.telegram and Config.NOTIFY_ERRORS:
                        self.telegram.notify_error(error_msg, f"Symbol: {symbol}")
                    
                    continue
                
                # Small delay between symbols
                time.sleep(0.5)
            
            self.logger.info(f"✅ Scan complete. Found {signals_found} signals")
            
        except Exception as e:
            error_msg = f"Error in market scan: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            
            if self.telegram and Config.NOTIFY_ERRORS:
                self.telegram.notify_error(error_msg)
    
    def show_status(self):
        """Display bot status"""
        try:
            uptime = datetime.now() - self.bot_start_time
            uptime_str = str(uptime).split('.')[0]
            
            balances = self.client.get_account_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            status = f"""
{'='*60}
🤖 CRYPTRO BOT STATUS
{'='*60}
Uptime: {uptime_str}
Start Time: {self.bot_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}

💰 Account: ${usdt_balance:.2f} USDT
📊 Trades: {self.total_trades} (Win Rate: {win_rate:.1f}%)
📈 Daily P&L: {self.risk_manager.daily_pnl:.2f}%

📦 Open Positions: {len(self.order_manager.open_positions)}
🔴 Consecutive Losses: {self.risk_manager.consecutive_losses}

⏰ Next Scan: {schedule.next_run().strftime('%H:%M:%S UTC') if schedule.next_run() else 'N/A'}
{'='*60}
            """
            
            self.logger.info(status)
            
        except Exception as e:
            self.logger.error(f"Error showing status: {e}")
    
    def generate_daily_report(self):
        """Generate daily performance report"""
        try:
            balances = self.client.get_account_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            total_balance = sum(
                bal.get('total', 0) 
                for bal in balances.values()
            )
            
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            report_data = {
                'daily_pnl': self.risk_manager.daily_pnl,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'win_rate': win_rate,
                'open_positions': len(self.order_manager.open_positions),
                'account_balance': total_balance,
                'available_balance': usdt_balance
            }
            
            # Log report
            self.logger.performance_report(report_data)
            
            # Risk report
            risk_report = self.risk_manager.get_risk_report()
            self.logger.info(risk_report)
            
            # Telegram notification
            if (self.telegram and 
                Config.ENABLE_TELEGRAM and 
                Config.NOTIFY_DAILY_REPORT):
                self.telegram.notify_daily_report(report_data)
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
    
    def emergency_stop(self):
        """Emergency stop all trading"""
        self.logger.critical("🚨 EMERGENCY STOP ACTIVATED!")
        
        if self.telegram:
            self.telegram.notify_error(
                "EMERGENCY STOP",
                "Bot is stopping all trading activities immediately."
            )
        
        # Close all positions
        for symbol in list(self.order_manager.open_positions.keys()):
            self.logger.warning(f"Emergency closing: {symbol}")
            self.order_manager.close_position(symbol, "emergency")
        
        self.is_running = False
        
        if self.telegram:
            uptime = str(datetime.now() - self.bot_start_time).split('.')[0]
            self.telegram.notify_bot_status("stopped", uptime=uptime)
    
    def run(self):
        """Main bot execution loop"""
        self.is_running = True
        
        # Startup notification
        if self.telegram:
            self.telegram.notify_bot_status("started", version=Config.VERSION)
        
        self.logger.info("="*60)
        self.logger.info("🚀 CRYPTRO BOT STARTED 🚀")
        self.logger.info("="*60)
        
        # Initial status
        self.show_status()
        
        # Schedule tasks
        schedule.every(Config.CHECK_INTERVAL_MINUTES).minutes.do(self.scan_market)
        schedule.every(15).minutes.do(
            lambda: self.order_manager.check_open_positions(self.risk_manager, self.telegram)
        )
        schedule.every(1).hours.do(self.show_status)
        schedule.every().day.at("00:05").do(self.generate_daily_report)
        
        if Config.LOG_TO_FILE:
            schedule.every().day.at("00:10").do(self.logger.cleanup_old_logs)
        
        # Run initial scan
        self.scan_market()
        
        # Main loop
        try:
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt")
                    self.is_running = False
                    break
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    
                    if self.telegram and Config.NOTIFY_ERRORS:
                        self.telegram.notify_error("Main loop error", str(e))
                    
                    time.sleep(60)
        
        except Exception as e:
            self.logger.critical(f"Critical bot error: {e}")
            self.logger.debug(traceback.format_exc())
            
            if self.telegram:
                self.telegram.notify_error("CRITICAL BOT ERROR", str(e))
        
        finally:
            # Clean shutdown
            self.logger.info("Shutting down bot...")
            
            if self.telegram:
                uptime = str(datetime.now() - self.bot_start_time).split('.')[0]
                self.telegram.notify_bot_status("stopped", uptime=uptime)
            
            self.logger.info("Bot shutdown complete")

# ============================================
# INSTALLATION SCRIPT FOR TERMUX
# ============================================

def create_install_script():
    """Create installation script for Termux"""
    script = """#!/bin/bash
# Cryptro Bot Installation Script for Termux

echo "Installing Cryptro Bot..."

# Update packages
pkg update && pkg upgrade -y

# Install dependencies
pkg install python python-pip git wget -y
pkg install build-essential python-dev -y

# Create project directory
mkdir -p ~/cryptro-bot
cd ~/cryptro-bot

# Create Python script
cat > cryptro_bot.py << 'EOF'
""" + open(__file__).read() + """
EOF

# Create requirements file
cat > requirements.txt << 'EOF'
python-binance==1.0.19
pandas==2.0.3
numpy==1.24.3
ta==0.10.2
python-dotenv==1.0.0
schedule==1.2.0
colorama==0.4.6
requests==2.31.0
EOF

# Install Python packages
pip install -r requirements.txt

# Create .env template
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Binance API Keys
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Testnet (Optional)
# USE_TESTNET=false
# TESTNET_API_KEY=your_testnet_key
# TESTNET_API_SECRET=your_testnet_secret
EOF
    echo "Created .env file. Please edit it with your API keys."
fi

# Create startup script
cat > start.sh << 'EOF'
#!/bin/bash
cd ~/cryptro-bot
python cryptro_bot.py
EOF

chmod +x start.sh

# Create run-in-background script
cat > run_background.sh << 'EOF'
#!/bin/bash
cd ~/cryptro-bot
while true; do
    python cryptro_bot.py
    echo "Bot crashed at $(date). Restarting in 30 seconds..."
    sleep 30
done
EOF

chmod +x run_background.sh

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano ~/cryptro-bot/.env"
echo "2. Add your Binance API keys"
echo "3. (Optional) Set up Telegram for notifications"
echo ""
echo "To start the bot:"
echo "  cd ~/cryptro-bot"
echo "  ./start.sh"
echo ""
echo "To run in background:"
echo "  screen -S cryptro"
echo "  ./run_background.sh"
echo "  Press Ctrl+A then D to detach"
echo ""
echo "To reattach:"
echo "  screen -r cryptro"
echo ""
echo "For emergency stop, press Ctrl+C in the bot terminal"
"""

    with open('install_cryptro.sh', 'w') as f:
        f.write(script)
    
    print("📦 Installation script created: install_cryptro.sh")
    print("Run: chmod +x install_cryptro.sh && ./install_cryptro.sh")

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║         ENHANCED CRYPTRO BOT v2.0        ║
    ║    Multi-timeframe Trading on Binance    ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Check for install argument
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        create_install_script()
        sys.exit(0)
    
    # Check for help argument
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("""
Usage:
  python cryptro_bot.py           - Run the bot
  python cryptro_bot.py --install - Create installation script for Termux
  python cryptro_bot.py --help    - Show this help

Configuration:
  Edit .env file with your API keys before running

Features:
  • Multi-timeframe analysis (5m to 1D)
  • Risk management system
  • Telegram notifications
  • Detailed logging
  • No stop loss, 6% take profit
  • Uses all available balance per trade

Requirements:
  • Binance API keys
  • Python 3.7+
  • Internet connection
        """)
        sys.exit(0)
    
    # Run the bot
    try:
        bot = CryptroBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start bot: {e}")
        print(traceback.format_exc())
        sys.exit(1)
