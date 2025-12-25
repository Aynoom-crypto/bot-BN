# blockchain.py
import hashlib
import json
import time
import pickle
import os

print("Loading CPYTRO Blockchain System...")

class Transaction:
    def __init__(self, sender, receiver, amount, fee=0.001):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.transaction_id = hashlib.sha512(
            f"{sender}{receiver}{amount}{fee}{self.timestamp}".encode()
        ).hexdigest()
    
    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }

class Block:
    def __init__(self, index, transactions, previous_hash, difficulty=3):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.difficulty = difficulty
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{self.previous_hash}{self.nonce}"
        for tx in self.transactions:
            block_string += tx.transaction_id
        return hashlib.sha512(block_string.encode()).hexdigest()
    
    def mine_block(self, target_prefix):
        print(f"Mining block {self.index}...")
        start_time = time.time()
        
        while self.hash[:self.difficulty] != target_prefix:
            self.nonce += 1
            self.hash = self.calculate_hash()
            
            if self.nonce % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"  Tried {self.nonce:,} hashes... ({elapsed:.1f}s)")
        
        mining_time = time.time() - start_time
        print(f"✓ Block {self.index} mined in {mining_time:.1f}s (Nonce: {self.nonce})")
        return True

class CPYTROBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = 3
        self.mining_reward = 50
        self.total_supply = 210000000
        self.mined_coins = 0
        
        if not self.chain:
            self.create_genesis_block()
    
    def create_genesis_block(self):
        print("Creating Genesis Block...")
        genesis_tx = Transaction("0", "genesis_foundation", 1000000, 0)
        genesis_block = Block(0, [genesis_tx], "0", self.difficulty)
        genesis_block.mine_block("0" * self.difficulty)
        self.chain.append(genesis_block)
        self.mined_coins += 1000000
        print("✓ Genesis Block created!")

if __name__ == "__main__":
    # Test the blockchain
    bc = CPYTROBlockchain()
    print(f"Blockchain initialized with {len(bc.chain)} blocks")
