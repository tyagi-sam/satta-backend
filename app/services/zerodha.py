from kiteconnect import KiteConnect
from typing import Optional, Dict, List
from datetime import datetime
import json

from ..core.config import settings
from ..core.logger import logger
from ..models.trade import Trade, TradeSide, TradeStatus
from ..core.security import decrypt_sensitive_data

class ZerodhaService:
    def __init__(self, api_key: str = settings.ZERODHA_API_KEY):
        logger.info(f"Initializing Zerodha service with API key: {api_key}")
        self.kite = KiteConnect(api_key=api_key)
        self.kite.redirect_url = settings.ZERODHA_REDIRECT_URL
        logger.info(f"Set redirect URL to: {settings.ZERODHA_REDIRECT_URL}")
        
    def set_access_token(self, access_token: str):
        """Set the access token for API calls"""
        # If the token is encrypted, decrypt it first
        if access_token and len(access_token) > 100:  # Encrypted tokens are longer due to Fernet
            try:
                access_token = decrypt_sensitive_data(access_token)
                logger.debug("Successfully decrypted access token")
            except Exception as e:
                logger.error(f"Failed to decrypt access token: {str(e)}", exc_info=True)
                raise
        
        logger.debug(f"Setting access token: {access_token[:10]}...")
        self.kite.set_access_token(access_token)
    
    def get_login_url(self) -> str:
        """Get the Zerodha login URL for OAuth"""
        login_url = self.kite.login_url()
        logger.debug(f"Generated login URL: {login_url}")
        return login_url
    
    def generate_session(self, request_token: str) -> Dict:
        """Generate session from the request token"""
        logger.info(f"Generating session for request token: {request_token}")
        try:
            session = self.kite.generate_session(
                request_token=request_token,
                api_secret=settings.ZERODHA_API_SECRET
            )
            logger.info("Session generated successfully")
            return session
        except Exception as e:
            logger.error(f"Failed to generate session: {str(e)}", exc_info=True)
            raise
    
    def get_profile(self) -> Dict:
        """Get user profile information"""
        logger.debug("Fetching user profile")
        try:
            profile = self.kite.profile()
            logger.info(f"Retrieved profile for user: {profile.get('user_name')}")
            return profile
        except Exception as e:
            logger.error("Failed to fetch user profile", exc_info=True)
            raise
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        logger.debug("Fetching positions")
        try:
            positions = self.kite.positions()["net"]
            logger.info(f"Retrieved {len(positions)} positions")
            return positions
        except Exception as e:
            logger.error("Failed to fetch positions", exc_info=True)
            raise
    
    def get_orders(self) -> List[Dict]:
        """Get today's orders"""
        logger.debug("Fetching orders")
        try:
            orders = self.kite.orders()
            logger.info(f"Retrieved {len(orders)} orders")
            return orders
        except Exception as e:
            logger.error("Failed to fetch orders", exc_info=True)
            raise
    
    def get_trades(self) -> List[Dict]:
        """Get today's trades"""
        logger.debug("Fetching trades")
        try:
            trades = self.kite.trades()
            logger.info(f"Retrieved {len(trades)} trades")
            return trades
        except Exception as e:
            logger.error("Failed to fetch trades", exc_info=True)
            raise
    
    def parse_trade(self, order_data: Dict) -> Optional[Trade]:
        """Parse Zerodha order data into our Trade model"""
        try:
            logger.debug(f"Parsing trade data for order ID: {order_data.get('order_id')}")
            trade = Trade(
                zerodha_order_id=str(order_data["order_id"]),
                symbol=order_data["tradingsymbol"],
                side=TradeSide.BUY if order_data["transaction_type"] == "BUY" else TradeSide.SELL,
                quantity=order_data["quantity"],
                price=float(order_data["average_price"] or order_data["price"]),
                status=TradeStatus.COMPLETE if order_data["status"] == "COMPLETE" else TradeStatus.OPEN,
                executed_at=datetime.fromisoformat(order_data["order_timestamp"]),
                trigger_price=float(order_data["trigger_price"]) if order_data.get("trigger_price") else None,
            )
            logger.info(f"Successfully parsed trade for {trade.symbol}")
            return trade
        except Exception as e:
            logger.error(f"Error parsing trade: {e}", exc_info=True)
            return None
    
    def calculate_pnl(self, trades: List[Trade]) -> float:
        """Calculate realized PnL for a list of trades"""
        pnl = 0.0
        position_map = {}  # symbol -> (quantity, avg_price)
        
        for trade in sorted(trades, key=lambda x: x.executed_at):
            symbol = trade.symbol
            qty = trade.quantity
            price = trade.price
            
            if trade.side == TradeSide.BUY:
                if symbol not in position_map:
                    position_map[symbol] = (qty, price)
                else:
                    curr_qty, curr_avg = position_map[symbol]
                    new_qty = curr_qty + qty
                    new_avg = (curr_qty * curr_avg + qty * price) / new_qty
                    position_map[symbol] = (new_qty, new_avg)
            else:  # SELL
                if symbol in position_map:
                    curr_qty, curr_avg = position_map[symbol]
                    pnl += (price - curr_avg) * min(qty, curr_qty)
                    new_qty = curr_qty - qty
                    if new_qty <= 0:
                        del position_map[symbol]
                    else:
                        position_map[symbol] = (new_qty, curr_avg)
                        
        return pnl

    def get_holdings(self) -> List[Dict]:
        """Get user's holdings"""
        logger.debug("Fetching holdings")
        try:
            holdings = self.kite.holdings()
            logger.info(f"Retrieved {len(holdings)} holdings")
            return holdings
        except Exception as e:
            logger.error("Failed to fetch holdings", exc_info=True)
            raise

zerodha_service = ZerodhaService() 