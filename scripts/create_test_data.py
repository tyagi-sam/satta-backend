import os
import sys
from datetime import datetime, date

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import SQLALCHEMY_DATABASE_URL
from app.models import User, Group, GroupMember, Trade
from app.models.trade import InstrumentType, TradeSide, TradeStatus, TradeType
from app.core.security import get_password_hash

def create_test_data():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create test users
        leader = User(
            email="leader@test.com",
            password=get_password_hash("testpass123"),
            is_active=True
        )
        member = User(
            email="member@test.com",
            password=get_password_hash("testpass123"),
            is_active=True
        )
        db.add_all([leader, member])
        db.flush()
        
        print(f"Created leader (ID: {leader.id}) and member (ID: {member.id})")
        
        # Create test group
        group = Group(
            name="Test Trading Group",
            description="A test group for trading",
            leader_id=leader.id
        )
        db.add(group)
        db.flush()
        
        print(f"Created group (ID: {group.id})")
        
        # Add member to group
        group_member = GroupMember(
            user_id=member.id,
            group_id=group.id,
            status="ACTIVE"
        )
        db.add(group_member)
        
        # Create test trades
        trades = [
            Trade(
                leader_id=leader.id,
                group_id=group.id,
                zerodha_order_id="test_order_1",
                symbol="RELIANCE",
                instrument_type=InstrumentType.EQUITY,
                side=TradeSide.BUY,
                quantity=10,
                price=2500.0,
                trade_type=TradeType.REGULAR,
                status=TradeStatus.COMPLETE,
                executed_at=datetime.now(),
                current_market_price=2550.0,
                realized_pnl=500.0
            ),
            Trade(
                leader_id=leader.id,
                group_id=group.id,
                zerodha_order_id="test_order_2",
                symbol="NIFTY23D14800CE",
                instrument_type=InstrumentType.OPTION,
                side=TradeSide.BUY,
                quantity=50,
                price=150.0,
                trade_type=TradeType.REGULAR,
                status=TradeStatus.OPEN,
                strike_price=14800,
                expiry_date=date(2023, 12, 28),
                option_type="CE",
                current_market_price=180.0,
                unrealized_pnl=1500.0
            )
        ]
        db.add_all(trades)
        
        # Commit all changes
        db.commit()
        print(f"Created {len(trades)} test trades")
        print("\nTest data created successfully!")
        print(f"\nUse these credentials to test:")
        print(f"Leader Email: leader@test.com")
        print(f"Member Email: member@test.com")
        print(f"Password for both: testpass123")
        
    except Exception as e:
        print(f"Error creating test data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data() 