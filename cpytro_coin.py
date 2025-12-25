#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🪙 CPYTRO COIN - สกุลเงินดิจิทัลขุดผ่านมือถือได้
🚀 เวอร์ชัน Termux พร้อมใช้งานทันที
📱 สำหรับ Android และคอมพิวเตอร์
"""

import hashlib
import json
import time
import os
import sys
import random
from datetime import datetime

# ============================================================================
# ตั้งค่าสีสำหรับ Terminal (ถ้ารองรับ)
# ============================================================================

class Colors:
    """สีสำหรับ Terminal"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_color(text, color):
    """พิมพ์ข้อความสี"""
    try:
        print(f"{color}{text}{Colors.END}")
    except:
        print(text)

def print_header(text):
    """พิมพ์หัวข้อ"""
    print_color("\n" + "="*60, Colors.CYAN)
    print_color(f"          {text}", Colors.BOLD + Colors.CYAN)
    print_color("="*60, Colors.CYAN)

def print_success(text):
    """พิมพ์ข้อความสำเร็จ"""
    print_color(f"✅ {text}", Colors.GREEN)

def print_error(text):
    """พิมพ์ข้อความผิดพลาด"""
    print_color(f"❌ {text}", Colors.RED)

def print_info(text):
    """พิมพ์ข้อมูล"""
    print_color(f"ℹ️  {text}", Colors.BLUE)

def print_warning(text):
    """พิมพ์คำเตือน"""
    print_color(f"⚠️  {text}", Colors.YELLOW)

# ============================================================================
# ส่วนที่ 1: Blockchain Core (ใจกลางระบบ)
# ============================================================================

class CPYTROTransaction:
    """ธุรกรรม CPYTRO"""
    def __init__(self, sender, receiver, amount, fee=0.001):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.tx_id = self._calculate_hash()
    
    def _calculate_hash(self):
        """คำนวณแฮชของธุรกรรม"""
        data_string = f"{self.sender}{self.receiver}{self.amount}{self.fee}{self.timestamp}"
        return hashlib.sha512(data_string.encode()).hexdigest()
    
    def to_dict(self):
        """แปลงเป็น dictionary"""
        return {
            'id': self.tx_id[:16] + '...',
            'from': self.sender[:10] + '...' if len(self.sender) > 10 else self.sender,
            'to': self.receiver[:10] + '...' if len(self.receiver) > 10 else self.receiver,
            'amount': self.amount,
            'fee': self.fee,
            'time': datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')
        }
    
    def full_dict(self):
        """ข้อมูลเต็มสำหรับบันทึก"""
        return {
            'tx_id': self.tx_id,
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }

class CPYTROBlock:
    """บล็อกของ CPYTRO"""
    
    def __init__(self, index, transactions, previous_hash, difficulty=3):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.difficulty = difficulty
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        """คำนวณแฮชของบล็อก"""
        block_string = f"{self.index}{self.timestamp}{self.previous_hash}{self.nonce}"
        for tx in self.transactions:
            block_string += tx.tx_id
        return hashlib.sha512(block_string.encode()).hexdigest()
    
    def mine_block(self):
        """ขุดบล็อกนี้"""
        print_info(f"เริ่มขุดบล็อก #{self.index} (ความยาก: {self.difficulty})")
        
        target_prefix = "0" * self.difficulty
        start_time = time.time()
        hash_count = 0
        
        # แสดงแอนิเมชันการขุด
        animations = ["⛏️ ", "⚒️ ", "🔨 ", "⛰️ "]
        anim_index = 0
        
        while self.hash[:self.difficulty] != target_prefix:
            self.nonce += 1
            self.hash = self.calculate_hash()
            hash_count += 1
            
            # แสดงความคืบหน้าทุก 1000 hash
            if hash_count % 1000 == 0:
                elapsed = time.time() - start_time
                hashrate = hash_count / elapsed if elapsed > 0 else 0
                
                # แอนิเมชัน
                anim = animations[anim_index % len(animations)]
                anim_index += 1
                
                print(f"\r{anim} พยายามแล้ว {hash_count:,} hashes ({hashrate:.0f} H/s)...", end="", flush=True)
        
        mining_time = time.time() - start_time
        print(f"\r{' ' * 80}\r", end="")  # ล้างบรรทัด
        
        print_success(f"ขุดบล็อก #{self.index} สำเร็จ!")
        print_info(f"ใช้เวลา: {mining_time:.1f} วินาที | Nonce: {self.nonce:,} | Hash: {self.hash[:16]}...")
        
        return True
    
    def to_dict(self):
        """แปลงบล็อกเป็น dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.full_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'difficulty': self.difficulty,
            'hash': self.hash
        }

class CPYTROBlockchain:
    """บล็อกเชนหลักของ CPYTRO"""
    
    def __init__(self, data_dir="cpytro_data"):
        self.data_dir = data_dir
        self.chain_file = os.path.join(data_dir, "blockchain.json")
        self.chain = []
        self.pending_transactions = []
        self.difficulty = 3  # ตั้งต่ำสำหรับมือถือ
        self.block_reward = 50.0
        self.total_supply = 210000000
        self.mined_coins = 0
        
        # สร้างโฟลเดอร์ข้อมูลถ้ายังไม่มี
        os.makedirs(data_dir, exist_ok=True)
        
        # โหลดหรือสร้างบล็อกเชน
        self.load_blockchain()
        
        # สร้าง Genesis Block ถ้ายังไม่มี
        if len(self.chain) == 0:
            self.create_genesis_block()
    
    def create_genesis_block(self):
        """สร้างบล็อกแรกของระบบ"""
        print_info("กำลังสร้าง Genesis Block...")
        
        genesis_tx = CPYTROTransaction(
            "0",  # ส่งจากระบบ
            "cpytro_genesis",  # กระเป๋า genesis
            1000000,  # 1 ล้านเหรียญเริ่มต้น
            0
        )
        
        genesis_block = CPYTROBlock(0, [genesis_tx], "0", 1)  # ความยาก 1
        genesis_block.hash = hashlib.sha512(b"genesis").hexdigest()
        self.chain.append(genesis_block)
        self.mined_coins += 1000000
        
        self.save_blockchain()
        print_success("Genesis Block สร้างสำเร็จ!")
    
    def add_transaction(self, sender, receiver, amount, fee=0.001):
        """เพิ่มธุรกรรมใหม่"""
        if amount <= 0:
            print_error("จำนวนต้องมากกว่า 0")
            return False
        
        if sender != "0":  # ถ้าไม่ใช่ระบบ
            # ตรวจสอบยอดเงิน (แบบง่าย)
            balance = self.get_balance(sender)
            if balance < amount + fee:
                print_error(f"ยอดเงินไม่พอ (มี: {balance:.2f}, ต้องการ: {amount + fee:.2f})")
                return False
        
        tx = CPYTROTransaction(sender, receiver, amount, fee)
        self.pending_transactions.append(tx)
        
        print_success(f"เพิ่มธุรกรรม: {sender[:8]}... → {receiver[:8]}... ({amount} CPYTRO)")
        return True
    
    def mine_new_block(self, miner_address):
        """ขุดบล็อกใหม่"""
        if not self.pending_transactions:
            print_warning("ไม่มีธุรกรรมรอขุด")
            return None
        
        print_info(f"กำลังขุดบล็อกใหม่... (ธุรกรรมรออยู่: {len(self.pending_transactions)})")
        
        # เพิ่มธุรกรรมรางวัลการขุด
        reward_tx = CPYTROTransaction(
            "0",  # จากระบบ
            miner_address,
            self.block_reward,
            0
        )
        self.pending_transactions.append(reward_tx)
        
        # สร้างบล็อกใหม่
        previous_hash = self.chain[-1].hash if self.chain else "0"
        new_block = CPYTROBlock(
            len(self.chain),
            self.pending_transactions.copy(),
            previous_hash,
            self.difficulty
        )
        
        # ขุดบล็อก
        if new_block.mine_block():
            self.chain.append(new_block)
            self.pending_transactions = []
            self.mined_coins += self.block_reward
            
            # บันทึกลงไฟล์
            self.save_blockchain()
            
            print_success(f"เพิ่มบล็อก #{new_block.index} เข้าสู่บล็อกเชน!")
            print_info(f"ได้รับรางวัล: {self.block_reward} CPYTRO")
            
            return new_block
        else:
            # ถ้าขุดไม่สำเร็จ ลบธุรกรรมรางวัล
            if self.pending_transactions and self.pending_transactions[-1].receiver == miner_address:
                self.pending_transactions.pop()
            print_error("ขุดบล็อกไม่สำเร็จ")
            return None
    
    def get_balance(self, address):
        """คำนวณยอดเงินในกระเป๋า"""
        balance = 0.0
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.receiver == address:
                    balance += tx.amount
                if tx.sender == address and tx.sender != "0":
                    balance -= (tx.amount + tx.fee)
        
        return balance
    
    def get_blockchain_info(self):
        """ดึงข้อมูลสรุบบล็อกเชน"""
        return {
            'total_blocks': len(self.chain),
            'difficulty': self.difficulty,
            'block_reward': self.block_reward,
            'total_supply': self.total_supply,
            'mined_coins': self.mined_coins,
            'pending_transactions': len(self.pending_transactions),
            'percentage_mined': (self.mined_coins / self.total_supply * 100) if self.total_supply > 0 else 0
        }
    
    def load_blockchain(self):
        """โหลดบล็อกเชนจากไฟล์"""
        if os.path.exists(self.chain_file):
            try:
                with open(self.chain_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # โหลดข้อมูลพื้นฐาน
                self.difficulty = data.get('difficulty', 3)
                self.mined_coins = data.get('mined_coins', 0)
                
                # โหลดบล็อก
                if 'chain' in data:
                    for block_data in data['chain']:
                        transactions = [
                            CPYTROTransaction(
                                tx['sender'],
                                tx['receiver'],
                                tx['amount'],
                                tx.get('fee', 0.001)
                            ) for tx in block_data['transactions']
                        ]
                        
                        block = CPYTROBlock(
                            block_data['index'],
                            transactions,
                            block_data['previous_hash'],
                            block_data.get('difficulty', 3)
                        )
                        block.timestamp = block_data['timestamp']
                        block.nonce = block_data['nonce']
                        block.hash = block_data['hash']
                        
                        self.chain.append(block)
                
                print_success(f"โหลดบล็อกเชนสำเร็จ: {len(self.chain)} บล็อก")
                return True
                
            except Exception as e:
                print_error(f"ไม่สามารถโหลดบล็อกเชนได้: {e}")
                self.chain = []
        
        return False
    
    def save_blockchain(self):
        """บันทึกลงไฟล์"""
        try:
            data = {
                'difficulty': self.difficulty,
                'block_reward': self.block_reward,
                'total_supply': self.total_supply,
                'mined_coins': self.mined_coins,
                'last_updated': time.time(),
                'chain': [block.to_dict() for block in self.chain]
            }
            
            with open(self.chain_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print_error(f"ไม่สามารถบันทึกบล็อกเชนได้: {e}")
            return False

# ============================================================================
# ส่วนที่ 2: Mobile Wallet (กระเป๋าสตางค์มือถือ)
# ============================================================================

class CPYTROWalletManager:
    """จัดการกระเป๋าสตางค์ CPYTRO"""
    
    def __init__(self, data_dir="cpytro_data"):
        self.data_dir = data_dir
        self.wallet_file = os.path.join(data_dir, "wallets.json")
        self.wallets = []
        self.blockchain = CPYTROBlockchain(data_dir)
        
        os.makedirs(data_dir, exist_ok=True)
        self.load_wallets()
    
    def generate_address(self, nickname=""):
        """สร้างที่อยู่กระเป๋าใหม่"""
        # ใช้เวลาและข้อมูลสุ่มสร้างที่อยู่
        random_data = f"{nickname}{time.time()}{random.getrandbits(256)}"
        
        # สร้าง public address จาก SHA512
        public_key = hashlib.sha512(random_data.encode()).hexdigest()
        
        # ที่อยู่ CPYTRO (รูปแบบ: CPYTRO_ + 40 ตัวอักษรแรก)
        address = f"CPYTRO_{public_key[:40]}"
        
        return address
    
    def create_wallet(self, nickname="กระเป๋าหลัก", show_warning=True):
        """สร้างกระเป๋าสตางค์ใหม่"""
        if not nickname:
            nickname = f"กระเป๋า_{len(self.wallets) + 1}"
        
        print_info(f"กำลังสร้างกระเป๋า: '{nickname}'")
        
        # สร้างที่อยู่ใหม่
        address = self.generate_address(nickname)
        
        # ข้อมูลกระเป๋า
        wallet_data = {
            'id': len(self.wallets) + 1,
            'nickname': nickname,
            'address': address,
            'created': time.time(),
            'balance': 0.0,
            'transactions': []
        }
        
        self.wallets.append(wallet_data)
        self.save_wallets()
        
        print_success("สร้างกระเป๋าสำเร็จ!")
        print(f"📛 ชื่อ: {nickname}")
        print(f"📍 ที่อยู่: {address}")
        
        if show_warning:
            print_header("⚠️  คำเตือนสำคัญ")
            print("1. 📝 บันทึกที่อยู่นี้ไว้ในที่ปลอดภัย!")
            print("2. 🔒 อย่าแชร์ให้ใครรู้!")
            print("3. 💾 สำรองข้อมูลเป็นประจำ!")
            print("4. ❌ หากลืม = เสียเงินทั้งหมด!")
        
        return address
    
    def import_wallet(self, address, nickname=""):
        """นำเข้า/เพิ่มกระเป๋าจากที่อยู่ที่มี"""
        # ตรวจสอบว่ามีอยู่แล้วหรือไม่
        for wallet in self.wallets:
            if wallet['address'] == address:
                print_warning(f"ที่อยู่นี้มีอยู่แล้วในชื่อ: {wallet['nickname']}")
                return False
        
        if not nickname:
            nickname = f"กระเป๋านำเข้า_{len(self.wallets) + 1}"
        
        wallet_data = {
            'id': len(self.wallets) + 1,
            'nickname': nickname,
            'address': address,
            'created': time.time(),
            'balance': 0.0,
            'transactions': []
        }
        
        self.wallets.append(wallet_data)
        self.save_wallets()
        
        print_success(f"นำเข้ากระเป๋า '{nickname}' สำเร็จ")
        return True
    
    def get_wallet_balance(self, address):
        """ดึงยอดเงินจากบล็อกเชน"""
        return self.blockchain.get_balance(address)
    
    def update_all_balances(self):
        """อัพเดทยอดเงินทุกกระเป๋าจากบล็อกเชน"""
        updated = 0
        for wallet in self.wallets:
            old_balance = wallet['balance']
            new_balance = self.get_wallet_balance(wallet['address'])
            
            if old_balance != new_balance:
                wallet['balance'] = new_balance
                updated += 1
        
        if updated > 0:
            self.save_wallets()
            print_success(f"อัพเดทยอดเงิน {updated} กระเป๋า")
        
        return updated
    
    def list_wallets(self):
        """แสดงรายการกระเป๋าทั้งหมด"""
        if not self.wallets:
            print_warning("ยังไม่มีกระเป๋าสตางค์")
            return
        
        self.update_all_balances()
        
        print_header("กระเป๋าสตางค์ของคุณ")
        
        total_balance = 0
        for wallet in self.wallets:
            print(f"\n[{wallet['id']}] 📛 {wallet['nickname']}")
            print(f"   📍 {wallet['address']}")
            print(f"   💰 {wallet['balance']:.2f} CPYTRO")
            print(f"   📅 สร้าง: {datetime.fromtimestamp(wallet['created']).strftime('%Y-%m-%d %H:%M')}")
            
            total_balance += wallet['balance']
        
        print_header("สรุปยอดเงิน")
        print(f"💰 ยอดรวมทั้งหมด: {total_balance:.2f} CPYTRO")
        print(f"📊 จำนวนกระเป๋า: {len(self.wallets)}")
    
    def get_wallet_by_id(self, wallet_id):
        """ดึงกระเป๋าจาก ID"""
        try:
            wallet_id = int(wallet_id)
            for wallet in self.wallets:
                if wallet['id'] == wallet_id:
                    return wallet
        except:
            pass
        return None
    
    def get_wallet_by_address(self, address):
        """ดึงกระเป๋าจากที่อยู่"""
        for wallet in self.wallets:
            if wallet['address'] == address:
                return wallet
        return None
    
    def delete_wallet(self, wallet_id):
        """ลบกระเป๋า"""
        wallet = self.get_wallet_by_id(wallet_id)
        if not wallet:
            print_error(f"ไม่พบกระเป๋า ID: {wallet_id}")
            return False
        
        confirm = input(f"แน่ใจว่าต้องการลบกระเป๋า '{wallet['nickname']}'? (y/n): ")
        if confirm.lower() == 'y':
            self.wallets = [w for w in self.wallets if w['id'] != wallet['id']]
            # รีเซ็ต ID
            for i, w in enumerate(self.wallets, 1):
                w['id'] = i
            self.save_wallets()
            print_success(f"ลบกระเป๋า '{wallet['nickname']}' สำเร็จ")
            return True
        else:
            print_info("ยกเลิกการลบ")
            return False
    
    def save_wallets(self):
        """บันทึกข้อมูลกระเป๋าลงไฟล์"""
        try:
            data = {
                'wallets': self.wallets,
                'last_updated': time.time(),
                'total_wallets': len(self.wallets)
            }
            
            with open(self.wallet_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print_error(f"ไม่สามารถบันทึกข้อมูลกระเป๋าได้: {e}")
            return False
    
    def load_wallets(self):
        """โหลดข้อมูลกระเป๋าจากไฟล์"""
        if os.path.exists(self.wallet_file):
            try:
                with open(self.wallet_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.wallets = data.get('wallets', [])
                print_success(f"โหลดกระเป๋า {len(self.wallets)} อันสำเร็จ")
                return True
            except Exception as e:
                print_error(f"ไม่สามารถโหลดข้อมูลกระเป๋าได้: {e}")
                self.wallets = []
        return False
    
    def backup_wallets(self):
        """สำรองข้อมูลกระเป๋า"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.data_dir, f"wallets_backup_{timestamp}.json")
        
        try:
            with open(self.wallet_file, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            print_success(f"สำรองข้อมูลสำเร็จ: {backup_file}")
            return backup_file
        except Exception as e:
            print_error(f"ไม่สามารถสำรองข้อมูลได้: {e}")
            return None
    
    def get_wallet_stats(self):
        """ดึงสถิติของกระเป๋า"""
        if not self.wallets:
            return None
        
        total_balance = sum(w['balance'] for w in self.wallets)
        
        return {
            'total_wallets': len(self.wallets),
            'total_balance': total_balance,
            'average_balance': total_balance / len(self.wallets) if len(self.wallets) > 0 else 0,
            'oldest_wallet': min(w['created'] for w in self.wallets),
            'newest_wallet': max(w['created'] for w in self.wallets)
        }

# ============================================================================
# ส่วนที่ 3: Mobile Miner (ระบบขุดสำหรับมือถือ)
# ============================================================================

class CPYTROMiner:
    """ระบบขุด CPYTRO สำหรับมือถือ"""
    
    def __init__(self, wallet_address=None, data_dir="cpytro_data"):
        self.wallet_address = wallet_address
        self.data_dir = data_dir
        self.blockchain = CPYTROBlockchain(data_dir)
        self.wallet_manager = CPYTROWalletManager(data_dir)
        
        self.is_mining = False
        self.mining_start_time = 0
        self.total_hashes = 0
        self.blocks_mined = 0
        
        # สถิติการขุด
        self.mining_stats = {
            'total_mining_time': 0,
            'total_blocks_mined': 0,
            'total_coins_earned': 0,
            'best_hash_rate': 0
        }
        
        # โหลดสถิติ
        self.load_stats()
    
    def start_mining_session(self, duration_minutes=5):
        """เริ่มเซสชันการขุด"""
        if not self.wallet_address:
            print_error("ต้องตั้งค่าที่อยู่กระเป๋าก่อนเริ่มขุด")
            return False
        
        wallet = self.wallet_manager.get_wallet_by_address(self.wallet_address)
        if not wallet:
            print_error(f"ไม่พบกระเป๋าที่อยู่: {self.wallet_address[:20]}...")
            return False
        
        print_header("เริ่มเซสชันการขุด")
        print(f"👛 กระเป๋า: {wallet['nickname']}")
        print(f"📍 ที่อยู่: {self.wallet_address[:20]}...")
        print(f"💰 ยอดเงินปัจจุบัน: {wallet['balance']:.2f} CPYTRO")
        print(f"⏰ ระยะเวลาขุด: {duration_minutes} นาที")
        print(f"⚙️  ความยาก: {self.blockchain.difficulty}")
        print(f"🎯 รางวัลต่อบล็อก: {self.blockchain.block_reward} CPYTRO")
        
        print("\n📱 คำแนะนำ:")
        print("• ชาร์จแบตเตอรี่ขณะขุด")
        print("• ใช้ WiFi จะเร็วขึ้น")
        print("• กด Ctrl+C เพื่อหยุดเมื่อใดก็ได้")
        print("-" * 60)
        
        input("กด Enter เพื่อเริ่มขุด...")
        
        self.is_mining = True
        self.mining_start_time = time.time()
        end_time = self.mining_start_time + (duration_minutes * 60)
        session_hashes = 0
        session_blocks = 0
        
        print_info("🚀 เริ่มขุด CPYTRO!")
        
        try:
            while self.is_mining and time.time() < end_time:
                # สร้างธุรกรรมทดสอบเพื่อเพิ่มข้อมูลในบล็อก
                test_tx = CPYTROTransaction(
                    self.wallet_address,
                    "cpytro_network",
                    0.001,  # ค่าธรรมเนียมเล็กน้อย
                    0.0001
                )
                self.blockchain.add_transaction(
                    self.wallet_address,
                    "cpytro_network",
                    0.001,
                    0.0001
                )
                
                # ขุดบล็อกใหม่
                block = self.blockchain.mine_new_block(self.wallet_address)
                
                if block:
                    session_blocks += 1
                    self.blocks_mined += 1
                    
                    # อัพเดทยอดเงินในกระเป๋า
                    self.wallet_manager.update_all_balances()
                    
                    # แสดงผล
                    remaining = (end_time - time.time()) / 60
                    if remaining > 0:
                        print_info(f"⏳ เหลือเวลา: {remaining:.1f} นาที | บล็อกที่ขุดได้: {session_blocks}")
                
                # พักสักครู่
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n" + "="*60)
            print_info("หยุดขุดโดยผู้ใช้")
        
        finally:
            self.is_mining = False
            session_duration = (time.time() - self.mining_start_time) / 60
            
            # อัพเดทสถิติ
            self.mining_stats['total_mining_time'] += session_duration
            self.mining_stats['total_blocks_mined'] += session_blocks
            self.mining_stats['total_coins_earned'] += session_blocks * self.blockchain.block_reward
            
            # บันทึกสถิติ
            self.save_stats()
            
            # แสดงสรุป
            print_header("สรุปผลการขุด")
            print(f"⏱️  เวลาที่ใช้: {session_duration:.1f} นาที")
            print(f"📦 บล็อกที่ขุดได้: {session_blocks}")
            print(f"💰 ได้รับทั้งหมด: {session_blocks * self.blockchain.block_reward} CPYTRO")
            
            if session_duration > 0:
                print(f"⚡ ความเร็วเฉลี่ย: {session_blocks/session_duration:.1f} บล็อก/นาที")
            
            # แสดงสถิติทั้งหมด
            self.show_lifetime_stats()
            
            # แสดงยอดเงินล่าสุด
            wallet = self.wallet_manager.get_wallet_by_address(self.wallet_address)
            if wallet:
                print(f"💳 ยอดเงินปัจจุบัน: {wallet['balance']:.2f} CPYTRO")
        
        return True
    
    def show_lifetime_stats(self):
        """แสดงสถิติการขุดตลอดชีพ"""
        print_header("สถิติการขุดตลอดชีพ")
        print(f"⏱️  เวลาขุดทั้งหมด: {self.mining_stats['total_mining_time']:.1f} นาที")
        print(f"📦 บล็อกที่ขุดได้ทั้งหมด: {self.mining_stats['total_blocks_mined']}")
        print(f"💰 เหรียญที่ได้รับทั้งหมด: {self.mining_stats['total_coins_earned']:.2f} CPYTRO")
        
        if self.mining_stats['total_mining_time'] > 0:
            avg_blocks_per_hour = (self.mining_stats['total_blocks_mined'] / self.mining_stats['total_mining_time']) * 60
            print(f"📈 เฉลี่ย: {avg_blocks_per_hour:.1f} บล็อก/ชั่วโมง")
    
    def load_stats(self):
        """โหลดสถิติการขุด"""
        stats_file = os.path.join(self.data_dir, "mining_stats.json")
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.mining_stats = json.load(f)
            except:
                pass
    
    def save_stats(self):
        """บันทึกสถิติการขุด"""
        stats_file = os.path.join(self.data_dir, "mining_stats.json")
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.mining_stats, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def set_wallet_address(self, address):
        """ตั้งค่าที่อยู่กระเป๋าสำหรับขุด"""
        self.wallet_address = address
        print_success(f"ตั้งค่ากระเป๋าสำหรับขุดเป็น: {address[:20]}...")
        return True

# ============================================================================
# ส่วนที่ 4: User Interface (ส่วนติดต่อผู้ใช้)
# ============================================================================

class CPYTROUI:
    """ส่วนติดต่อผู้ใช้ CPYTRO Coin"""
    
    def __init__(self):
        self.data_dir = "cpytro_data"
        self.wallet_manager = None
        self.blockchain = None
        self.miner = None
        
        # สร้างโฟลเดอร์ข้อมูล
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.init_system()
    
    def init_system(self):
        """เริ่มต้นระบบ"""
        print_color("\n" + "="*60, Colors.PURPLE)
        print_color("        🪙 CPYTRO COIN - Mobile Mining System", Colors.BOLD + Colors.PURPLE)
        print_color("="*60, Colors.PURPLE)
        
        time.sleep(1)
        
        # ตรวจสอบ Python version
        print_info(f"Python Version: {sys.version.split()[0]}")
        print_info(f"Data Directory: {os.path.abspath(self.data_dir)}")
        
        # ตรวจสอบหน่วยความจำ
        try:
            import psutil
            memory = psutil.virtual_memory()
            print_info(f"Available Memory: {memory.available / 1024 / 1024:.0f} MB")
        except:
            pass
        
        # โหลดระบบ
        print_info("กำลังโหลดระบบ...")
        self.wallet_manager = CPYTROWalletManager(self.data_dir)
        self.blockchain = CPYTROBlockchain(self.data_dir)
        self.miner = CPYTROMiner(data_dir=self.data_dir)
        
        print_success("ระบบพร้อมใช้งาน!")
        
        # แสดงข้อมูลพื้นฐาน
        bc_info = self.blockchain.get_blockchain_info()
        print(f"\n📊 สถิติบล็อกเชน:")
        print(f"   📦 บล็อกทั้งหมด: {bc_info['total_blocks']}")
        print(f"   💎 เหรียญที่ขุดแล้ว: {bc_info['mined_coins']:,}/{bc_info['total_supply']:,}")
        print(f"   📈 ขุดแล้ว: {bc_info['percentage_mined']:.6f}%")
        
        time.sleep(2)
    
    def clear_screen(self):
        """ล้างหน้าจอ"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_main_menu(self):
        """แสดงเมนูหลัก"""
        self.clear_screen()
        
        print_header("เมนูหลัก CPYTRO Coin")
        
        # แสดงข้อมูลสรุป
        wallet_stats = self.wallet_manager.get_wallet_stats()
        if wallet_stats:
            print(f"👛 กระเป๋า: {wallet_stats['total_wallets']} อัน | 💰 ยอดรวม: {wallet_stats['total_balance']:.2f} CPYTRO")
        else:
            print("👛 ยังไม่มีกระเป๋าสตางค์")
        
        bc_info = self.blockchain.get_blockchain_info()
        print(f"🔗 บล็อกเชน: {bc_info['total_blocks']} บล็อก | ⛏️  ขุดแล้ว: {bc_info['percentage_mined']:.6f}%")
        
        print("\n" + "="*60)
        print("📱 เลือกเมนู:")
        print("  [1] 📝 จัดการกระเป๋าสตางค์")
        print("  [2] ⛏️  ระบบขุดเหรียญ")
        print("  [3] 🔗 ข้อมูลบล็อกเชน")
        print("  [4] ⚙️  การตั้งค่าระบบ")
        print("  [5] 💾 การสำรองข้อมูล")
        print("  [6] ℹ️  ข้อมูลและช่วยเหลือ")
        print("  [7] 🚪 ออกจากโปรแกรม")
        print("="*60)
        
        choice = input("\n👉 กรุณาเลือกหมายเลข (1-7): ").strip()
        
        return choice
    
    def wallet_menu(self):
        """เมนูจัดการกระเป๋า"""
        while True:
            self.clear_screen()
            print_header("จัดการกระเป๋าสตางค์")
            
            print("  [1] 📝 สร้างกระเป๋าใหม่")
            print("  [2] 📋 ดูรายการกระเป๋าทั้งหมด")
            print("  [3] 🔄 อัพเดทยอดเงินทั้งหมด")
            print("  [4] 📥 นำเข้ากระเป๋าจากที่อยู่")
            print("  [5] ❌ ลบกระเป๋า")
            print("  [6] ↩️  กลับสู่เมนูหลัก")
            
            choice = input("\n👉 เลือกหมายเลข (1-6): ").strip()
            
            if choice == "1":
                self.create_wallet()
            elif choice == "2":
                self.list_wallets()
            elif choice == "3":
                self.update_balances()
            elif choice == "4":
                self.import_wallet()
            elif choice == "5":
                self.delete_wallet()
            elif choice == "6":
                return
            else:
                print_error("กรุณาเลือกหมายเลข 1-6 เท่านั้น")
                time.sleep(1)
    
    def create_wallet(self):
        """สร้างกระเป๋าใหม่"""
        self.clear_screen()
        print_header("สร้างกระเป๋าสตางค์ใหม่")
        
        nickname = input("📛 ตั้งชื่อกระเป๋า (หรือกด Enter สำหรับ 'กระเป๋าหลัก'): ").strip()
        
        address = self.wallet_manager.create_wallet(
            nickname if nickname else "กระเป๋าหลัก",
            show_warning=True
        )
        
        input("\n👉 กด Enter เพื่อกลับสู่เมนู...")
    
    def list_wallets(self):
        """แสดงรายการกระเป๋า"""
        self.clear_screen()
        self.wallet_manager.list_wallets()
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def update_balances(self):
        """อัพเดทยอดเงิน"""
        self.clear_screen()
        print_header("อัพเดทยอดเงิน")
        
        updated = self.wallet_manager.update_all_balances()
        if updated == 0:
            print_info("ไม่มียอดเงินที่ต้องอัพเดท")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def import_wallet(self):
        """นำเข้ากระเป๋า"""
        self.clear_screen()
        print_header("นำเข้ากระเป๋าจากที่อยู่")
        
        address = input("📍 กรุณาใส่ที่อยู่ CPYTRO ที่ต้องการนำเข้า: ").strip()
        
        if not address.startswith("CPYTRO_"):
            print_warning("ที่อยู่ CPYTRO ควรเริ่มต้นด้วย 'CPYTRO_'")
            confirm = input("ต้องการดำเนินการต่อไหม? (y/n): ")
            if confirm.lower() != 'y':
                return
        
        nickname = input("📛 ตั้งชื่อให้กระเป๋านี้ (หรือกด Enter สำหรับชื่ออัตโนมัติ): ").strip()
        
        if self.wallet_manager.import_wallet(address, nickname):
            print_success("นำเข้ากระเป๋าสำเร็จ!")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def delete_wallet(self):
        """ลบกระเป๋า"""
        self.clear_screen()
        print_header("ลบกระเป๋าสตางค์")
        
        self.wallet_manager.list_wallets()
        
        wallet_id = input("\n👉 กรอกหมายเลขกระเป๋าที่ต้องการลบ (หรือกด Enter เพื่อยกเลิก): ").strip()
        
        if wallet_id:
            self.wallet_manager.delete_wallet(wallet_id)
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def mining_menu(self):
        """เมนูระบบขุด"""
        while True:
            self.clear_screen()
            print_header("ระบบขุดเหรียญ CPYTRO")
            
            # แสดงข้อมูลกระเป๋าปัจจุบัน
            if self.miner.wallet_address:
                wallet = self.wallet_manager.get_wallet_by_address(self.miner.wallet_address)
                if wallet:
                    print(f"🎯 กระเป๋าปัจจุบัน: {wallet['nickname']} ({wallet['balance']:.2f} CPYTRO)")
                else:
                    print("⚠️  ไม่พบข้อมูลกระเป๋าปัจจุบัน")
            else:
                print("⚠️  ยังไม่ได้ตั้งค่ากระเป๋าสำหรับขุด")
            
            print("\n  [1] ⛏️  เริ่มขุดเหรียญ")
            print("  [2] 🎯 เลือกกระเป๋าสำหรับขุด")
            print("  [3] 📊 ดูสถิติการขุด")
            print("  [4] ⚙️  ตั้งค่าระบบขุด")
            print("  [5] ↩️  กลับสู่เมนูหลัก")
            
            choice = input("\n👉 เลือกหมายเลข (1-5): ").strip()
            
            if choice == "1":
                self.start_mining()
            elif choice == "2":
                self.select_mining_wallet()
            elif choice == "3":
                self.show_mining_stats()
            elif choice == "4":
                self.mining_settings()
            elif choice == "5":
                return
            else:
                print_error("กรุณาเลือกหมายเลข 1-5 เท่านั้น")
                time.sleep(1)
    
    def select_mining_wallet(self):
        """เลือกกระเป๋าสำหรับขุด"""
        self.clear_screen()
        print_header("เลือกกระเป๋าสำหรับขุด")
        
        if not self.wallet_manager.wallets:
            print_warning("คุณยังไม่มีกระเป๋าสตางค์")
            print("กรุณาสร้างกระเป๋าก่อนเลือกสำหรับขุด")
            input("\n👉 กด Enter เพื่อกลับ...")
            return
        
        self.wallet_manager.list_wallets()
        
        wallet_id = input("\n👉 กรอกหมายเลขกระเป๋าที่ต้องการใช้ขุด: ").strip()
        
        wallet = self.wallet_manager.get_wallet_by_id(wallet_id)
        if wallet:
            self.miner.set_wallet_address(wallet['address'])
            print_success(f"ตั้งค่ากระเป๋า '{wallet['nickname']}' สำหรับขุดสำเร็จ")
        else:
            print_error("ไม่พบกระเป๋าที่ระบุ")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def start_mining(self):
        """เริ่มขุดเหรียญ"""
        self.clear_screen()
        
        if not self.miner.wallet_address:
            print_error("กรุณาเลือกกระเป๋าสำหรับขุดก่อน")
            input("\n👉 กด Enter เพื่อกลับ...")
            return
        
        print_header("เริ่มเซสชันการขุด")
        
        print("⏰ เลือกเวลาขุด:")
        print("  [1] 1 นาที (ทดลอง)")
        print("  [2] 5 นาที (แนะนำ)")
        print("  [3] 10 นาที (ขุดจริง)")
        print("  [4] 30 นาที (ขุดนาน)")
        print("  [5] กำหนดเอง")
        
        choice = input("\n👉 เลือกหมายเลข (1-5): ").strip()
        
        duration_map = {'1': 1, '2': 5, '3': 10, '4': 30}
        
        if choice in duration_map:
            duration = duration_map[choice]
        elif choice == '5':
            try:
                custom = int(input("👉 ระบุเวลาขุด (นาที): "))
                duration = max(1, min(custom, 180))  # จำกัดไม่เกิน 3 ชั่วโมง
            except:
                print_error("กรุณากรอกตัวเลข")
                duration = 5
        else:
            duration = 5
        
        # เริ่มขุด
        self.miner.start_mining_session(duration)
        
        input("\n👉 กด Enter เพื่อกลับสู่เมนู...")
    
    def show_mining_stats(self):
        """แสดงสถิติการขุด"""
        self.clear_screen()
        print_header("สถิติการขุด")
        
        self.miner.show_lifetime_stats()
        
        # แสดงสถิติจากบล็อกเชน
        bc_info = self.blockchain.get_blockchain_info()
        print(f"\n📊 สถิติระบบ:")
        print(f"   ⚙️  ความยากปัจจุบัน: {bc_info['difficulty']}")
        print(f"   💎 รางวัลต่อบล็อก: {bc_info['block_reward']} CPYTRO")
        print(f"   📦 ธุรกรรมรอขุด: {bc_info['pending_transactions']}")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def mining_settings(self):
        """ตั้งค่าระบบขุด"""
        self.clear_screen()
        print_header("ตั้งค่าระบบขุด")
        
        print(f"⚙️  การตั้งค่าปัจจุบัน:")
        print(f"   ความยาก: {self.blockchain.difficulty}")
        print(f"   รางวัลต่อบล็อก: {self.blockchain.block_reward}")
        print(f"   โฟลเดอร์ข้อมูล: {self.data_dir}")
        
        print("\n🔧 ตัวเลือก:")
        print("  [1] ปรับความยากในการขุด")
        print("  [2] เปลี่ยนรางวัลต่อบล็อก")
        print("  [3] รีเซ็ตสถิติการขุด")
        print("  [4] กลับ")
        
        choice = input("\n👉 เลือกหมายเลข (1-4): ").strip()
        
        if choice == "1":
            try:
                new_diff = int(input("ตั้งค่าความยากใหม่ (1-5, ค่าปัจจุบัน=3): "))
                if 1 <= new_diff <= 5:
                    self.blockchain.difficulty = new_diff
                    self.blockchain.save_blockchain()
                    print_success(f"ตั้งค่าความยากเป็น {new_diff} สำเร็จ")
                else:
                    print_error("กรุณาระบุค่าระหว่าง 1-5")
            except:
                print_error("กรุณากรอกตัวเลขเท่านั้น")
        
        elif choice == "2":
            try:
                new_reward = float(input("ตั้งค่ารางวัลใหม่ (1-100, ค่าปัจจุบัน=50): "))
                if 1 <= new_reward <= 100:
                    self.blockchain.block_reward = new_reward
                    self.blockchain.save_blockchain()
                    print_success(f"ตั้งค่ารางวัลเป็น {new_reward} CPYTRO สำเร็จ")
                else:
                    print_error("กรุณาระบุค่าระหว่าง 1-100")
            except:
                print_error("กรุณากรอกตัวเลขเท่านั้น")
        
        elif choice == "3":
            confirm = input("แน่ใจว่าต้องการรีเซ็ตสถิติการขุดทั้งหมด? (y/n): ")
            if confirm.lower() == 'y':
                self.miner.mining_stats = {
                    'total_mining_time': 0,
                    'total_blocks_mined': 0,
                    'total_coins_earned': 0,
                    'best_hash_rate': 0
                }
                self.miner.save_stats()
                print_success("รีเซ็ตสถิติการขุดสำเร็จ")
        
        if choice != "4":
            input("\n👉 กด Enter เพื่อกลับ...")
    
    def blockchain_menu(self):
        """เมนูข้อมูลบล็อกเชน"""
        self.clear_screen()
        print_header("ข้อมูลบล็อกเชน CPYTRO")
        
        info = self.blockchain.get_blockchain_info()
        
        print(f"\n📊 สถิติบล็อกเชน:")
        print(f"   📦 จำนวนบล็อกทั้งหมด: {info['total_blocks']}")
        print(f"   ⚙️  ความยากปัจจุบัน: {info['difficulty']}")
        print(f"   💎 รางวัลต่อบล็อก: {info['block_reward']} CPYTRO")
        print(f"   🏦 จำนวนเหรียญทั้งหมด: {info['total_supply']:,} CPYTRO")
        print(f"   ⛏️  เหรียญที่ขุดแล้ว: {info['mined_coins']:,} CPYTRO")
        print(f"   📈 เปอร์เซ็นต์ที่ขุดแล้ว: {info['percentage_mined']:.6f}%")
        print(f"   📋 ธุรกรรมรอขุด: {info['pending_transactions']}")
        
        if info['total_blocks'] > 0:
            print(f"\n📦 บล็อกล่าสุด:")
            for i, block in enumerate(self.blockchain.chain[-3:], 1):
                print(f"\n   บล็อก #{block.index}:")
                print(f"      🕒 เวลา: {datetime.fromtimestamp(block.timestamp).strftime('%H:%M:%S')}")
                print(f"      📋 ธุรกรรม: {len(block.transactions)}")
                print(f"      🔗 แฮช: {block.hash[:16]}...")
                print(f"      🔢 Nonce: {block.nonce:,}")
        
        print("\n" + "="*60)
        print("ℹ️  ข้อมูลเทคนิค:")
        print("• อัลกอริทึม: SHA512")
        print("• ชนิด: Proof-of-Work (PoW)")
        print("• Halving: ทุก 210,000 บล็อก")
        print("• จำนวนเหรียญสูงสุด: 210,000,000")
        print("• เหมาะสำหรับ: การขุดบนมือถือ")
        print("="*60)
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def settings_menu(self):
        """เมนูตั้งค่าระบบ"""
        while True:
            self.clear_screen()
            print_header("ตั้งค่าระบบ")
            
            print(f"📁 โฟลเดอร์ข้อมูล: {os.path.abspath(self.data_dir)}")
            print(f"🐍 เวอร์ชัน Python: {sys.version.split()[0]}")
            print(f"💾 จำนวนไฟล์ข้อมูล: {len(os.listdir(self.data_dir)) if os.path.exists(self.data_dir) else 0}")
            
            print("\n  [1] 🔍 ตรวจสอบระบบ")
            print("  [2] 📁 เปลี่ยนโฟลเดอร์ข้อมูล")
            print("  [3] 🗑️  ล้างข้อมูลทั้งหมด")
            print("  [4] ↩️  กลับสู่เมนูหลัก")
            
            choice = input("\n👉 เลือกหมายเลข (1-4): ").strip()
            
            if choice == "1":
                self.system_check()
            elif choice == "2":
                self.change_data_dir()
            elif choice == "3":
                self.reset_system()
            elif choice == "4":
                return
            else:
                print_error("กรุณาเลือกหมายเลข 1-4 เท่านั้น")
                time.sleep(1)
    
    def system_check(self):
        """ตรวจสอบระบบ"""
        self.clear_screen()
        print_header("ตรวจสอบระบบ")
        
        checks = []
        
        # 1. ตรวจสอบ Python
        checks.append(("Python Version", sys.version.split()[0], "✅"))
        
        # 2. ตรวจสอบโฟลเดอร์ข้อมูล
        if os.path.exists(self.data_dir):
            checks.append(("Data Directory", "Found", "✅"))
            file_count = len([f for f in os.listdir(self.data_dir) if f.endswith('.json')])
            checks.append(("Data Files", f"{file_count} files", "✅" if file_count > 0 else "⚠️"))
        else:
            checks.append(("Data Directory", "Not Found", "❌"))
        
        # 3. ตรวจสอบไฟล์สำคัญ
        important_files = ['blockchain.json', 'wallets.json']
        for file in important_files:
            path = os.path.join(self.data_dir, file)
            if os.path.exists(path):
                size = os.path.getsize(path)
                checks.append((file, f"{size} bytes", "✅"))
            else:
                checks.append((file, "Not Found", "❌"))
        
        # 4. ตรวจสอบหน่วยความจำ
        try:
            import psutil
            memory = psutil.virtual_memory()
            checks.append(("Available Memory", f"{memory.available / 1024 / 1024:.0f} MB", "✅"))
        except:
            checks.append(("Memory Info", "N/A", "⚠️"))
        
        # แสดงผล
        print("\n📋 ผลการตรวจสอบ:")
        print("-" * 60)
        for name, value, status in checks:
            print(f"{status} {name}: {value}")
        print("-" * 60)
        
        # แนะนำ
        errors = sum(1 for _, _, status in checks if status == "❌")
        if errors == 0:
            print_success("ระบบอยู่ในสภาพดี!")
        else:
            print_warning(f"พบปัญหา {errors} จุด")
            print("แนะนำให้ใช้เมนู 'ล้างข้อมูลทั้งหมด' และเริ่มใหม่")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def change_data_dir(self):
        """เปลี่ยนโฟลเดอร์ข้อมูล"""
        self.clear_screen()
        print_header("เปลี่ยนโฟลเดอร์ข้อมูล")
        
        print(f"โฟลเดอร์ปัจจุบัน: {os.path.abspath(self.data_dir)}")
        
        new_dir = input("\n👉 กรอกโฟลเดอร์ใหม่ (หรือกด Enter เพื่อยกเลิก): ").strip()
        
        if new_dir:
            if os.path.exists(self.data_dir):
                # ถามว่าต้องการย้ายไฟล์หรือไม่
                move = input("ต้องการย้ายไฟล์ข้อมูลไปยังโฟลเดอร์ใหม่ไหม? (y/n): ")
                if move.lower() == 'y':
                    import shutil
                    try:
                        shutil.move(self.data_dir, new_dir)
                        print_success(f"ย้ายไฟล์ข้อมูลไปยัง {new_dir} สำเร็จ")
                    except Exception as e:
                        print_error(f"ไม่สามารถย้ายไฟล์ได้: {e}")
            
            self.data_dir = new_dir
            os.makedirs(new_dir, exist_ok=True)
            
            # โหลดระบบใหม่
            self.wallet_manager = CPYTROWalletManager(self.data_dir)
            self.blockchain = CPYTROBlockchain(self.data_dir)
            self.miner = CPYTROMiner(data_dir=self.data_dir)
            
            print_success(f"ตั้งค่าโฟลเดอร์ข้อมูลเป็น {new_dir} สำเร็จ")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def reset_system(self):
        """ล้างข้อมูลทั้งหมด"""
        self.clear_screen()
        print_header("ล้างข้อมูลทั้งหมด")
        
        print_warning("⚠️  คำเตือน: การกระทำนี้จะลบข้อมูลทั้งหมด!")
        print("• ข้อมูลกระเป๋าสตางค์ทั้งหมดจะหาย")
        print("• ประวัติธุรกรรมทั้งหมดจะถูกลบ")
        print("• สถิติการขุดทั้งหมดจะถูกลบ")
        print("• ไม่สามารถกู้คืนได้!")
        
        confirm1 = input("\nพิมพ์ 'DELETE ALL' เพื่อยืนยัน: ")
        if confirm1 != "DELETE ALL":
            print_info("ยกเลิกการล้างข้อมูล")
            input("\n👉 กด Enter เพื่อกลับ...")
            return
        
        confirm2 = input("แน่ใจ 100% ไหม? พิมพ์ 'YES' เพื่อยืนยันอีกครั้ง: ")
        if confirm2 != "YES":
            print_info("ยกเลิกการล้างข้อมูล")
            input("\n👉 กด Enter เพื่อกลับ...")
            return
        
        # ล้างข้อมูล
        import shutil
        try:
            if os.path.exists(self.data_dir):
                shutil.rmtree(self.data_dir)
                print_success("ลบโฟลเดอร์ข้อมูลสำเร็จ")
            
            # สร้างใหม่
            os.makedirs(self.data_dir, exist_ok=True)
            
            # โหลดระบบใหม่
            self.wallet_manager = CPYTROWalletManager(self.data_dir)
            self.blockchain = CPYTROBlockchain(self.data_dir)
            self.miner = CPYTROMiner(data_dir=self.data_dir)
            
            print_success("ระบบถูกรีเซ็ตแล้ว สามารถเริ่มต้นใหม่ได้")
            
        except Exception as e:
            print_error(f"เกิดข้อผิดพลาด: {e}")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def backup_menu(self):
        """เมนูสำรองข้อมูล"""
        self.clear_screen()
        print_header("สำรองข้อมูล")
        
        print("📁 ข้อมูลที่สามารถสำรองได้:")
        print("  • ข้อมูลกระเป๋าสตางค์")
        print("  • บล็อกเชน")
        print("  • สถิติการขุด")
        
        print("\n🔧 ตัวเลือก:")
        print("  [1] 💾 สำรองข้อมูลทั้งหมด")
        print("  [2] 📤 นำเข้าข้อมูลสำรอง")
        print("  [3] 📋 ดูรายการสำรองข้อมูล")
        print("  [4] ↩️  กลับสู่เมนูหลัก")
        
        choice = input("\n👉 เลือกหมายเลข (1-4): ").strip()
        
        if choice == "1":
            self.create_backup()
        elif choice == "2":
            self.restore_backup()
        elif choice == "3":
            self.list_backups()
        elif choice == "4":
            return
        else:
            print_error("กรุณาเลือกหมายเลข 1-4 เท่านั้น")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def create_backup(self):
        """สร้างไฟล์สำรอง"""
        import zipfile
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"cpytro_backup_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # เพิ่มไฟล์ทั้งหมดในโฟลเดอร์ข้อมูล
                for root, dirs, files in os.walk(self.data_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.data_dir)
                        zipf.write(file_path, arcname)
                
                # เพิ่มไฟล์ระบบ
                zipf.write(__file__, "cpytro_coin.py")
            
            size = os.path.getsize(backup_file)
            print_success(f"สร้างไฟล์สำรองสำเร็จ: {backup_file}")
            print_info(f"ขนาดไฟล์: {size:,} bytes")
            
            # แสดงข้อมูลในไฟล์
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                files = zipf.namelist()
                print_info(f"ไฟล์ที่สำรอง: {len(files)} files")
                for f in files[:5]:  # แสดง 5 ไฟล์แรก
                    print(f"  • {f}")
                if len(files) > 5:
                    print(f"  • ... และอีก {len(files) - 5} ไฟล์")
        
        except Exception as e:
            print_error(f"ไม่สามารถสร้างไฟล์สำรองได้: {e}")
    
    def list_backups(self):
        """แสดงรายการไฟล์สำรอง"""
        backup_files = [f for f in os.listdir('.') if f.startswith('cpytro_backup_') and f.endswith('.zip')]
        
        if not backup_files:
            print_warning("ไม่พบไฟล์สำรอง")
            return
        
        print_header("รายการไฟล์สำรอง")
        
        for i, backup in enumerate(sorted(backup_files, reverse=True), 1):
            size = os.path.getsize(backup)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup))
            print(f"\n[{i}] {backup}")
            print(f"   📏 ขนาด: {size:,} bytes")
            print(f"   📅 วันที่: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📊 รวมทั้งหมด: {len(backup_files)} ไฟล์")
    
    def restore_backup(self):
        """กู้คืนข้อมูลจากไฟล์สำรอง"""
        backup_files = [f for f in os.listdir('.') if f.startswith('cpytro_backup_') and f.endswith('.zip')]
        
        if not backup_files:
            print_warning("ไม่พบไฟล์สำรอง")
            return
        
        print_header("กู้คืนข้อมูลจากไฟล์สำรอง")
        self.list_backups()
        
        try:
            choice = int(input("\n👉 เลือกหมายเลขไฟล์ที่ต้องการกู้คืน: "))
            if 1 <= choice <= len(backup_files):
                backup_file = backup_files[choice - 1]
                
                print_warning(f"กำลังกู้คืนข้อมูลจาก: {backup_file}")
                print_warning("ข้อมูลปัจจุบันจะถูกแทนที่!")
                
                confirm = input("พิมพ์ 'RESTORE' เพื่อยืนยัน: ")
                if confirm != "RESTORE":
                    print_info("ยกเลิกการกู้คืน")
                    return
                
                import zipfile
                import shutil
                
                # สร้างสำรองข้อมูลปัจจุบันก่อน
                temp_dir = f"temp_backup_{int(time.time())}"
                if os.path.exists(self.data_dir):
                    shutil.copytree(self.data_dir, temp_dir)
                
                try:
                    # ล้างโฟลเดอร์ข้อมูล
                    if os.path.exists(self.data_dir):
                        shutil.rmtree(self.data_dir)
                    
                    os.makedirs(self.data_dir, exist_ok=True)
                    
                    # Extract ไฟล์สำรอง
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        zipf.extractall(self.data_dir)
                    
                    # โหลดระบบใหม่
                    self.wallet_manager = CPYTROWalletManager(self.data_dir)
                    self.blockchain = CPYTROBlockchain(self.data_dir)
                    self.miner = CPYTROMiner(data_dir=self.data_dir)
                    
                    print_success("กู้คืนข้อมูลสำเร็จ!")
                    print_info("ระบบถูกรีสตาร์ทด้วยข้อมูลสำรอง")
                    
                    # ลบ temp
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                
                except Exception as e:
                    print_error(f"การกู้คืนล้มเหลว: {e}")
                    
                    # กู้คืนจาก temp
                    if os.path.exists(temp_dir):
                        if os.path.exists(self.data_dir):
                            shutil.rmtree(self.data_dir)
                        shutil.move(temp_dir, self.data_dir)
                        print_info("กู้คืนข้อมูลเดิมสำเร็จ")
                    
                    # โหลดระบบใหม่
                    self.wallet_manager = CPYTROWalletManager(self.data_dir)
                    self.blockchain = CPYTROBlockchain(self.data_dir)
                    self.miner = CPYTROMiner(data_dir=self.data_dir)
            
            else:
                print_error("หมายเลขไม่ถูกต้อง")
        
        except ValueError:
            print_error("กรุณากรอกตัวเลขเท่านั้น")
    
    def help_menu(self):
        """เมนูช่วยเหลือ"""
        self.clear_screen()
        print_header("ช่วยเหลือและข้อมูล")
        
        print("📚 คู่มือการใช้งาน CPYTRO Coin")
        print("="*60)
        
        print("\n🚀 เริ่มต้นใช้งาน:")
        print("  1. สร้างกระเป๋าสตางค์ (เมนู 1 → 1)")
        print("  2. เริ่มขุดเหรียญ (เมนู 2 → 1)")
        print("  3. ตรวจสอบยอดเงิน (เมนู 1 → 2)")
        
        print("\n🔧 ฟีเจอร์หลัก:")
        print("  • 📝 สร้าง/จัดการกระเป๋าสตางค์")
        print("  • ⛏️  ขุดเหรียญผ่านมือถือ")
        print("  • 🔗 ดูข้อมูลบล็อกเชน")
        print("  • 💾 สำรอง/กู้คืนข้อมูล")
        
        print("\n⚙️  การตั้งค่าสำคัญ:")
        print("  • ความยากในการขุด (เริ่มต้น: 3)")
        print("  • รางวัลต่อบล็อก (เริ่มต้น: 50 CPYTRO)")
        print("  • โฟลเดอร์ข้อมูล (เริ่มต้น: cpytro_data/)")
        
        print("\n⚠️  ข้อควรระวัง:")
        print("  • บันทึกที่อยู่กระเป๋าให้ดี!")
        print("  • สำรองข้อมูลเป็นประจำ!")
        print("  • อย่าแชร์ข้อมูลส่วนตัว!")
        print("  • นี่เป็นโปรเจคทดลอง!")
        
        print("\n" + "="*60)
        print("📞 หากมีปัญหา:")
        print("  • ใช้เมนู 'ตรวจสอบระบบ'")
        print("  • ลอง 'ล้างข้อมูลทั้งหมด' แล้วเริ่มใหม่")
        print("  • ตรวจสอบว่ามีพื้นที่ว่างเพียงพอ")
        print("="*60)
        
        # แสดงข้อมูลเวอร์ชัน
        print(f"\n📊 ข้อมูลระบบ:")
        print(f"  เวอร์ชัน: 1.0.0")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  โฟลเดอร์ข้อมูล: {self.data_dir}")
        
        input("\n👉 กด Enter เพื่อกลับ...")
    
    def run(self):
        """รันโปรแกรมหลัก"""
        try:
            while True:
                choice = self.show_main_menu()
                
                if choice == "1":
                    self.wallet_menu()
                elif choice == "2":
                    self.mining_menu()
                elif choice == "3":
                    self.blockchain_menu()
                elif choice == "4":
                    self.settings_menu()
                elif choice == "5":
                    self.backup_menu()
                elif choice == "6":
                    self.help_menu()
                elif choice == "7":
                    print_color("\n🎉 ขอบคุณที่ใช้ CPYTRO Coin!", Colors.GREEN)
                    print_color("ฝากกดติดตามและแชร์ให้เพื่อนด้วยนะครับ! 😊", Colors.YELLOW)
                    break
                else:
                    print_error("กรุณาเลือกหมายเลข 1-7 เท่านั้น")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print_color("\n\n👋 ออกจากโปรแกรม", Colors.YELLOW)
        except Exception as e:
            print_error(f"เกิดข้อผิดพลาดร้ายแรง: {e}")
            input("\nกด Enter เพื่อปิดโปรแกรม...")

# ============================================================================
# ส่วนที่ 5: จุดเริ่มต้นโปรแกรม
# ============================================================================

def quick_setup():
    """ตั้งค่าระบบอย่างรวดเร็วสำหรับผู้ใช้ใหม่"""
    print_header("ตั้งค่าระบบอย่างรวดเร็ว")
    
    print("🎯 กำลังตั้งค่าระบบ CPYTRO Coin...")
    time.sleep(1)
    
    # สร้างระบบ
    ui = CPYTROUI()
    
    # ถามว่าต้องการสร้างกระเป๋าไหม
    print("\n📝 คุณต้องการสร้างกระเป๋าสตางค์แรกไหม?")
    print("  [1] ใช่ สร้างกระเป๋าใหม่")
    print("  [2] ไม่ ข้ามไปที่เมนูหลัก")
    
    choice = input("\n👉 เลือกหมายเลข (1-2): ").strip()
    
    if choice == "1":
        nickname = input("📛 ตั้งชื่อกระเป๋า (หรือกด Enter สำหรับ 'กระเป๋าหลัก'): ").strip()
        if not nickname:
            nickname = "กระเป๋าหลัก"
        
        address = ui.wallet_manager.create_wallet(nickname, show_warning=True)
        
        # ถามว่าต้องการเริ่มขุดทดลองไหม
        print("\n⛏️  คุณต้องการเริ่มขุดทดลอง 1 นาทีไหม?")
        test_mine = input("พิมพ์ 'y' เพื่อเริ่มขุดทดลอง หรือกด Enter เพื่อข้าม: ").strip()
        
        if test_mine.lower() == 'y':
            print_info("กำลังเริ่มขุดทดลอง 1 นาที...")
            ui.miner.set_wallet_address(address)
            ui.miner.start_mining_session(1)
    
    print_success("การตั้งค่าระบบเสร็จสิ้น!")
    time.sleep(2)
    
    return ui

def main():
    """ฟังก์ชันหลัก"""
    
    # แสดงหน้าต้อนรับ
    print_color("\n" + "="*60, Colors.PURPLE)
    print_color("        🚀 CPYTRO COIN - Mobile Mining Cryptocurrency", Colors.BOLD + Colors.PURPLE)
    print_color("="*60, Colors.PURPLE)
    print_color("✨ คุณสมบัติ:", Colors.CYAN)
    print_color("✓ ขุดผ่านมือถือได้", Colors.GREEN)
    print_color("✓ จำนวนจำกัด 210 ล้านเหรียญ", Colors.GREEN)
    print_color("✓ ใช้ SHA512 Algorithm", Colors.GREEN)
    print_color("✓ ใช้งานง่าย บน Termux ได้", Colors.GREEN)
    print_color("="*60, Colors.PURPLE)
    
    time.sleep(2)
    
    # ตรวจสอบอาร์กิวเมนต์
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            ui = quick_setup()
            ui.run()
            return
        elif sys.argv[1] == "--help":
            print("\n📚 วิธีใช้งาน:")
            print("  python cpytro_coin.py           # เริ่มโปรแกรมปกติ")
            print("  python cpytro_coin.py --setup   # ตั้งค่าระบบอย่างรวดเร็ว")
            print("  python cpytro_coin.py --help    # แสดงความช่วยเหลือ")
            return
    
    # เริ่มโปรแกรมปกติ
    try:
        ui = CPYTROUI()
        ui.run()
    except Exception as e:
        print_error(f"เกิดข้อผิดพลาดในการเริ่มต้นระบบ: {e}")
        print("\n🔄 ลองใช้โหมดตั้งค่าระบบ:")
        print("  python cpytro_coin.py --setup")
        input("\nกด Enter เพื่อปิด...")

# ============================================================================
# เริ่มโปรแกรม
# ============================================================================

if __name__ == "__main__":
    main()
