from binance.client import Client
from binance.enums import *
import time

class BinanceClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.client = Client(api_key, api_secret)
        if testnet:
            self.client.API_URL = 'https://testnet.binance.vision/api'
        
    def get_account_balance(self):
        """ดึงข้อมูลยอดเงินในบัญชี"""
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
            print(f"Error getting balance: {e}")
            return {}
    
    def get_klines(self, symbol, interval, limit=100):
        """ดึงข้อมูล candles"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return klines
        except Exception as e:
            print(f"Error getting klines for {symbol}: {e}")
            return []
    
    def get_all_trading_pairs(self, quote_asset='USDT'):
        """ดึงรายการทั้งหมดที่เทรดกับ USDT"""
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = []
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                if symbol.endswith(quote_asset) and symbol_info['status'] == 'TRADING':
                    # ตรวจสอบว่าไม่ใช่ leveraged token
                    if not ('UP' in symbol or 'DOWN' in symbol or 'BEAR' in symbol or 'BULL' in symbol):
                        symbols.append(symbol)
            return symbols
        except Exception as e:
            print(f"Error getting trading pairs: {e}")
            return []
    
    def place_order(self, symbol, side, quantity, price=None, order_type=ORDER_TYPE_MARKET):
        """ส่งคำสั่งซื้อขาย"""
        try:
            if order_type == ORDER_TYPE_MARKET:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    price=price,
                    timeInForce=TIME_IN_FORCE_GTC
                )
            return order
        except Exception as e:
            print(f"Error placing order for {symbol}: {e}")
            return None
    
    def place_take_profit_order(self, symbol, quantity, take_profit_price):
        """ตั้งคำสั่งขายแบบ限价 (limit sell) สำหรับ take profit"""
        try:
            # ปรับ quantity ให้ถูกต้องตาม lot size
            symbol_info = self.client.get_symbol_info(symbol)
            lot_size_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'),
                None
            )
            
            if lot_size_filter:
                step_size = float(lot_size_filter['stepSize'])
                quantity = self._adjust_to_step(quantity, step_size)
            
            order = self.client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=take_profit_price,
                timeInForce=TIME_IN_FORCE_GTC
            )
            return order
        except Exception as e:
            print(f"Error placing take profit order for {symbol}: {e}")
            return None
    
    def _adjust_to_step(self, quantity, step_size):
        """ปรับ quantity ให้ตรงกับ step size"""
        precision = len(str(step_size).split('.')[1]) if '.' in str(step_size) else 0
        adjusted = round(int(quantity / step_size) * step_size, precision)
        return adjusted
    
    def get_open_orders(self, symbol=None):
        """ดึงรายการคำสั่งที่ยังไม่สมบูรณ์"""
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            return self.client.get_open_orders()
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return []
