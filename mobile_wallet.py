# mobile_wallet.py
import hashlib
import json
import os
import time

print("Loading Mobile Wallet...")

class MobileWallet:
    def __init__(self):
        self.wallet_file = "cpytro_wallet.json"
        self.wallets = []
        self.load_wallets()
    
    def create_new_wallet(self, nickname=""):
        """Create a new CPYTRO wallet"""
        print("\n" + "="*50)
        print("Creating New CPYTRO Wallet")
        print("="*50)
        
        # Generate address from random data
        seed = f"{nickname}{time.time()}{os.urandom(32).hex()}"
        address = hashlib.sha512(seed.encode()).hexdigest()[:40]
        
        wallet_data = {
            'address': address,
            'nickname': nickname or f"Wallet_{len(self.wallets)+1}",
            'created': time.time(),
            'balance': 0.0,
            'transactions': []
        }
        
        self.wallets.append(wallet_data)
        self.save_wallets()
        
        print(f"\n✅ Wallet Created Successfully!")
        print(f"📛 Nickname: {wallet_data['nickname']}")
        print(f"📍 Address: {address}")
        print(f"💰 Balance: 0.0 CPYTRO")
        print("\n" + "="*50)
        print("⚠️  IMPORTANT: Save this address!")
        print("="*50)
        
        return address
    
    def load_wallets(self):
        """Load wallets from file"""
        if os.path.exists(self.wallet_file):
            try:
                with open(self.wallet_file, 'r') as f:
                    self.wallets = json.load(f)
                print(f"✓ Loaded {len(self.wallets)} wallet(s)")
                return True
            except:
                print("⚠️  Could not load wallet file")
                self.wallets = []
        return False
    
    def save_wallets(self):
        """Save wallets to file"""
        try:
            with open(self.wallet_file, 'w') as f:
                json.dump(self.wallets, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving wallets: {e}")
            return False
    
    def get_wallet_info(self, address=None):
        """Get information about a wallet"""
        if not self.wallets:
            return None
        
        if address:
            for wallet in self.wallets:
                if wallet['address'] == address:
                    return wallet
        elif self.wallets:
            return self.wallets[0]
        
        return None
    
    def list_wallets(self):
        """List all wallets"""
        if not self.wallets:
            print("No wallets found")
            return
        
        print("\n" + "="*50)
        print("Your CPYTRO Wallets")
        print("="*50)
        
        for i, wallet in enumerate(self.wallets, 1):
            print(f"\n{i}. 📛 {wallet['nickname']}")
            print(f"   📍 {wallet['address'][:20]}...")
            print(f"   💰 {wallet['balance']:.2f} CPYTRO")
            print(f"   📅 Created: {time.ctime(wallet['created'])}")
        
        print("="*50)
    
    def update_balance(self, address, amount):
        """Update wallet balance"""
        for wallet in self.wallets:
            if wallet['address'] == address:
                wallet['balance'] = wallet.get('balance', 0) + amount
                self.save_wallets()
                return True
        return False
