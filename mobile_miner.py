"""
Mobile-optimized miner for CpyTro
"""

import hashlib
import time
import threading
import json
import sys
import os
from typing import Optional
import logging

# เพิ่ม path สำหรับ imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import MOBILE_CONFIG, TARGET_BLOCK_TIME

class MobileMinerApp:
    """Mobile-optimized mining application"""
    
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.is_mining = False
        self.hash_rate = 0
        self.blocks_mined = 0
        self.total_rewards = 0.0
        self.last_update = time.time()
        
        # Mobile optimization
        self.battery_saver = MOBILE_CONFIG["battery_saver"]
        self.thermal_throttling = MOBILE_CONFIG["thermal_throttling"]
        self.background_mining = MOBILE_CONFIG["background_mining"]
        
        # Mining stats
        self.hash_count = 0
        self.start_time = 0
        
        # Thread management
        self.mining_thread = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MobileMiner")
    
    def start_mining(self):
        """Start mobile mining"""
        if self.is_mining:
            self.logger.info("Mining already in progress")
            return
        
        self.is_mining = True
        self.start_time = time.time()
        self.hash_count = 0
        
        self.logger.info(f"Starting mobile miner for address: {self.wallet_address}")
        self.logger.info("Battery saver mode: " + ("ON" if self.battery_saver else "OFF"))
        
        # Start mining in separate thread
        self.mining_thread = threading.Thread(target=self._mining_loop)
        self.mining_thread.daemon = True
        self.mining_thread.start()
    
    def stop_mining(self):
        """Stop mining"""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        self.logger.info("Mining stopped")
    
    def _mining_loop(self):
        """Main mining loop optimized for mobile"""
        self.logger.info("Mining loop started")
        
        # Simple mining algorithm for demonstration
        # In production, this would connect to the actual blockchain
        
        nonce = 0
        target = 0x0000ffff00000000000000000000000000000000000000000000000000000000
        
        while self.is_mining:
            # Create a simple block header for mining
            timestamp = int(time.time())
            data = f"{self.wallet_address}{timestamp}{nonce}"
            
            # Calculate hash
            hash_result = hashlib.sha256(data.encode()).hexdigest()
            self.hash_count += 1
            
            # Update hash rate every second
            current_time = time.time()
            if current_time - self.last_update >= 1.0:
                self.hash_rate = self.hash_count / (current_time - self.last_update)
                self.hash_count = 0
                self.last_update = current_time
            
            # Check if hash meets difficulty target
            if int(hash_result, 16) < target:
                self.blocks_mined += 1
                reward = self._calculate_reward()
                self.total_rewards += reward
                
                self.logger.info(f"Block mined! Reward: {reward} CPT")
                self.logger.info(f"Hash: {hash_result}")
                self.logger.info(f"Total blocks mined: {self.blocks_mined}")
                self.logger.info(f"Total rewards: {self.total_rewards} CPT")
            
            # Increment nonce
            nonce += 1
            
            # Mobile optimizations
            if self.battery_saver:
                # Sleep briefly to save battery
                time.sleep(0.001)
            
            if self.thermal_throttling:
                # Check temperature (simulated)
                if nonce % 10000 == 0:
                    # Simulated temperature check
                    time.sleep(0.01)
    
    def _calculate_reward(self) -> float:
        """Calculate block reward"""
        # Simplified reward calculation
        base_reward = 50.0
        halving_factor = self.blocks_mined // 210000
        
        for _ in range(halving_factor):
            base_reward /= 2
        
        return max(base_reward, 0)
    
    def get_stats(self) -> dict:
        """Get mining statistics"""
        current_time = time.time()
        elapsed = current_time - self.start_time if self.start_time > 0 else 0
        
        return {
            "status": "active" if self.is_mining else "inactive",
            "wallet_address": self.wallet_address,
            "hash_rate": self.hash_rate,
            "blocks_mined": self.blocks_mined,
            "total_rewards": self.total_rewards,
            "uptime": elapsed,
            "battery_saver": self.battery_saver,
            "background_mining": self.background_mining
        }
    
    def save_state(self, filename: str = "miner_state.json"):
        """Save miner state to file"""
        state = {
            "wallet_address": self.wallet_address,
            "blocks_mined": self.blocks_mined,
            "total_rewards": self.total_rewards,
            "last_update": time.time()
        }
        
        with open(filename, "w") as f:
            json.dump(state, f)
        
        self.logger.info(f"Miner state saved to {filename}")
    
    def load_state(self, filename: str = "miner_state.json"):
        """Load miner state from file"""
        try:
            with open(filename, "r") as f:
                state = json.load(f)
            
            self.blocks_mined = state.get("blocks_mined", 0)
            self.total_rewards = state.get("total_rewards", 0.0)
            self.logger.info(f"Miner state loaded from {filename}")
            
        except FileNotFoundError:
            self.logger.info("No saved state found, starting fresh")

def main():
    """Main function for mobile miner"""
    print("="*50)
    print("       CpyTro Mobile Miner")
    print("="*50)
    
    # Get wallet address
    wallet_address = input("Enter your wallet address: ").strip()
    
    if not wallet_address:
        print("Generating new wallet address...")
        # In production, generate a real address
        wallet_address = hashlib.sha256(os.urandom(32)).hexdigest()[:40]
        print(f"Your new address: {wallet_address}")
    
    # Create miner
    miner = MobileMinerApp(wallet_address)
    miner.load_state()
    
    # Main menu
    while True:
        print("\n" + "="*50)
        print("Menu:")
        print("1. Start Mining")
        print("2. Stop Mining")
        print("3. Show Stats")
        print("4. Save State")
        print("5. Exit")
        print("="*50)
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            miner.start_mining()
            print("Mining started...")
        elif choice == "2":
            miner.stop_mining()
            print("Mining stopped.")
        elif choice == "3":
            stats = miner.get_stats()
            print(f"\nMining Statistics:")
            print(f"Status: {stats['status']}")
            print(f"Address: {stats['wallet_address']}")
            print(f"Hash Rate: {stats['hash_rate']:.2f} H/s")
            print(f"Blocks Mined: {stats['blocks_mined']}")
            print(f"Total Rewards: {stats['total_rewards']:.8f} CPT")
            print(f"Uptime: {stats['uptime']:.1f} seconds")
        elif choice == "4":
            miner.save_state()
            print("State saved.")
        elif choice == "5":
            miner.stop_mining()
            miner.save_state()
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
