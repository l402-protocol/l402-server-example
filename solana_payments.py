import asyncio
from datetime import datetime
from typing import Optional, Dict, Tuple
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
import json
import os
import logging
from database import db
from offers import get_offer_by_id
import base64

# Constants
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
MASTER_KEY_FILE = "solana_master.key"
PAYMENT_TIMEOUT = 300  # 5 minutes in seconds

_solana_manager = None

def get_solana_manager():
    global _solana_manager
    if _solana_manager is None:
        _solana_manager = SolanaPaymentManager()
    return _solana_manager

class SolanaPaymentManager:
    def __init__(self):
        self.client = AsyncClient("https://api.mainnet-beta.solana.com")
        self.active_payments: Dict[str, Tuple[float, datetime]] = {}
        self._monitoring = False
        self.current_index = 0
        self.master_keypair = self._load_or_create_master_keypair()
        self._monitor_task = None
        
    def _load_or_create_master_keypair(self) -> Keypair:
        if os.path.exists(MASTER_KEY_FILE):
            try:
                with open(MASTER_KEY_FILE, 'r') as f:
                    key_data = json.load(f)
                    secret_bytes = base64.b64decode(key_data['secret_key'])
                    return Keypair.from_bytes(list(secret_bytes))
            except Exception as e:
                logging.warning(f"Failed to load master key, creating new one: {e}")
                # Fall through to create new keypair
        
        # Create new master keypair if none exists
        keypair = Keypair()
        with open(MASTER_KEY_FILE, 'w') as f:
            json.dump({
                'secret_key': base64.b64encode(bytes(keypair.to_bytes())).decode('utf-8'),
                'public_key': str(keypair.pubkey())
            }, f)
        return keypair

    def derive_payment_address(self, index: int) -> Keypair:
        # Derive a unique keypair using the index
        # Note: This is a simplified example. In production, you'd want to use
        # proper BIP44 derivation with Solana's derivation path
        seed = bytes(self.master_keypair.to_bytes()) + index.to_bytes(8, 'big')
        return Keypair.from_seed(seed[:32])  # Take first 32 bytes as new seed

    async def create_payment_address(self, amount: float) -> str:
        # Get next derived address
        self.current_index += 1
        derived_keypair = self.derive_payment_address(self.current_index)
        address = str(derived_keypair.pubkey())
        
        # Add to active payments
        self.active_payments[address] = (amount, datetime.now())
        
        # Start monitoring if not already running
        if not self._monitoring:
            self._monitor_task = asyncio.create_task(self._monitor_payments())
            self._monitoring = True
            
        return address

    async def check_usdc_balance(self, address: str) -> Optional[float]:
        try:
            token_accounts = await self.client.get_token_accounts_by_owner(
                owner=Pubkey.from_string(address),
                mint=Pubkey.from_string(USDC_MINT)
            )
            
            if token_accounts['result']['value']:
                balance = token_accounts['result']['value'][0]['account']['data']['parsed']['info']['tokenAmount']['uiAmount']
                return float(balance)
            return 0.0
        except Exception as e:
            print(f"Error checking balance: {e}")
            return None

    async def _monitor_payments(self):
        while True:
            current_time = datetime.now()
            addresses_to_remove = []
            
            for address, (expected_amount, start_time) in self.active_payments.items():
                # Check if payment has timed out
                if (current_time - start_time).total_seconds() > PAYMENT_TIMEOUT:
                    addresses_to_remove.append(address)
                    continue
                
                balance = await self.check_usdc_balance(address)
                if balance is not None and balance >= expected_amount:
                    # Payment received! Update status
                    await self._handle_successful_payment(address, balance)
                    addresses_to_remove.append(address)
            
            # Remove processed or timed out payments
            for address in addresses_to_remove:
                self.active_payments.pop(address, None)
            
            # Stop monitoring if no active payments
            if not self.active_payments:
                self._monitoring = False
                break
                
            await asyncio.sleep(10)  # Check every 10 seconds

    async def _handle_successful_payment(self, address: str, amount: float):
        try:
            # Get payment request from database
            payment_request = db.get_payment_request(address)
            if not payment_request:
                logging.error(f"Invalid payment request: {address}")
                return
                
            user_id = payment_request['user_id']
            offer_id = payment_request['offer_id']
            
            # Load offer details
            offer = get_offer_by_id(offer_id)
            if not offer:
                logging.error(f"Invalid offer: {offer_id}")
                return
            
            # Update user credits based on offer
            db.update_user_credits(user_id, offer['balance'])
            
            # Record the completed payment
            db.record_payment(
                payment_request_id=payment_request['id'],
                credits=offer['balance'],
                amount=int(amount * 100),  # Convert to cents
                currency='USDC',
            )
            
            logging.info(f"Successfully processed Solana payment for {amount} USDC to {address}")
            
        except Exception as e:
            logging.error(f"Error handling successful payment: {e}")

async def create_solana_charge(user_id: str, offer: dict, expiry: datetime) -> dict:
    """Create a new Solana payment request"""
    try:
        manager = get_solana_manager()
        amount = float(offer["amount"]) / 100  # Convert cents to dollars
        
        # Create new address for payment
        address = await manager.create_payment_address(amount)
        
        # Store payment request in database
        db.create_payment_request(
            request_id=address,
            user_id=user_id,
            offer_id=offer["offer_id"]
        )
        
        return {
            "address": address,
        }

    except Exception as e:
        logging.error(f"Error creating Solana payment: {e}")
        return None

async def create_solana_payment(amount, keypair):
    try:
        public_key = keypair.pubkey()
        # Create async client if needed
        client = AsyncClient("https://api.mainnet-beta.solana.com")
        
        # Add your async Solana payment creation logic here
        # Make sure to use await for any async calls
        
        return {
            "public_key": str(public_key),
            "amount": amount
        }
        
    except Exception as e:
        logger.error(f"Error creating Solana payment: {str(e)}")
        raise PaymentError("Failed to create Solana payment") 