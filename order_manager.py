class OrderManager:
    def __init__(self, binance_client, config):
        self.client = binance_client
        self.config = config
        self.open_positions = {}
        
    def calculate_position_size(self, symbol, signal_price):
        """คำนวณขนาด position"""
        try:
            # ดึงยอดเงินทั้งหมด
            balances = self.client.get_account_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            if usdt_balance < self.config.MIN_BALANCE_USDT:
                return 0
                
            if self.config.USE_ALL_BALANCE:
                # ใช้เงินทั้งหมด (หักค่า fee ประมาณ 0.1%)
                available = usdt_balance * 0.999
            else:
                # หรือใช้สูตรอื่นตามต้องการ
                available = usdt_balance / self.config.MAX_OPEN_POSITIONS
                
            # คำนวณ quantity
            quantity = available / signal_price
            
            # ตรวจสอบ minimum notional (ควรเป็น 10 USDT สำหรับ spot)
            notional = quantity * signal_price
            if notional < 10:  # Binance minimum
                return 0
                
            return quantity
            
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return 0
    
    def execute_buy(self, signal):
        """ดำเนินการซื้อตามสัญญาณ"""
        try:
            symbol = signal['symbol']
            
            # ตรวจสอบว่ายังไม่มี position นี้อยู่
            if symbol in self.open_positions:
                print(f"Already have position for {symbol}")
                return False
                
            # คำนวณ position size
            quantity = self.calculate_position_size(symbol, signal['price'])
            
            if quantity <= 0:
                print(f"Insufficient balance for {symbol}")
                return False
                
            # สั่งซื้อแบบ market order
            buy_order = self.client.place_order(
                symbol=symbol,
                side=SIDE_BUY,
                quantity=quantity,
                order_type=ORDER_TYPE_MARKET
            )
            
            if buy_order:
                # ตั้ง take profit order ทันที
                tp_order = self.client.place_take_profit_order(
                    symbol=symbol,
                    quantity=quantity,
                    take_profit_price=signal['take_profit']
                )
                
                if tp_order:
                    # บันทึก position
                    self.open_positions[symbol] = {
                        'buy_price': signal['price'],
                        'quantity': quantity,
                        'take_profit_price': signal['take_profit'],
                        'tp_order_id': tp_order['orderId'],
                        'timestamp': signal['timestamp']
                    }
                    print(f"Successfully bought {quantity} {symbol} at {signal['price']}")
                    print(f"Take profit set at {signal['take_profit']}")
                    return True
                else:
                    # ถ้าไม่สามารถตั้ง TP ได้ ให้ขายทิ้ง
                    print(f"Failed to set TP for {symbol}, selling...")
                    self.client.place_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        quantity=quantity,
                        order_type=ORDER_TYPE_MARKET
                    )
                    
        except Exception as e:
            print(f"Error executing buy for {signal['symbol']}: {e}")
            
        return False
    
    def check_open_positions(self):
        """ตรวจสอบและอัปเดตสถานะ positions"""
        try:
            completed_positions = []
            
            for symbol, position in list(self.open_positions.items()):
                # ตรวจสอบว่า TP order ยังคงอยู่หรือไม่
                open_orders = self.client.get_open_orders(symbol=symbol)
                tp_order_exists = any(
                    order['orderId'] == position['tp_order_id'] 
                    for order in open_orders
                )
                
                if not tp_order_exists:
                    # TP order ถูก execute แล้ว
                    print(f"Take profit executed for {symbol}")
                    completed_positions.append(symbol)
                    
            # ลบ positions ที่เสร็จสิ้นแล้ว
            for symbol in completed_positions:
                del self.open_positions[symbol]
                
        except Exception as e:
            print(f"Error checking open positions: {e}")
