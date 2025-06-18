import pytest
import asyncio
import websockets
import json
from httpx import AsyncClient
from datetime import datetime, date
from app.models import Trade, User, Group, GroupMember
from app.models.trade import InstrumentType, TradeSide, TradeStatus
from app.main import app

@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_db(session):
    # Create test users
    leader = User(
        email="leader@test.com",
        hashed_password="testpass",
        is_active=True
    )
    member = User(
        email="member@test.com",
        hashed_password="testpass",
        is_active=True
    )
    session.add_all([leader, member])
    session.flush()

    # Create test group
    group = Group(
        name="Test Group",
        leader_id=leader.id,
        description="Test group for trade history"
    )
    session.add(group)
    session.flush()

    # Add member to group
    group_member = GroupMember(
        user_id=member.id,
        group_id=group.id,
        status="ACTIVE"
    )
    session.add(group_member)
    
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
            status=TradeStatus.OPEN,
            strike_price=14800,
            expiry_date=date(2023, 12, 28),
            option_type="CE",
            current_market_price=180.0,
            unrealized_pnl=1500.0
        )
    ]
    session.add_all(trades)
    session.commit()

    return {
        "leader": leader,
        "member": member,
        "group": group,
        "trades": trades
    }

@pytest.mark.asyncio
async def test_get_leader_trades(test_client, test_db):
    # Test as group member
    response = await test_client.get(
        f"/trades/leader/{test_db['leader'].id}",
        headers={"Authorization": f"Bearer {create_test_token(test_db['member'])}"}
    )
    assert response.status_code == 200
    trades = response.json()
    assert len(trades) == 2
    
    # Test filtering by instrument type
    response = await test_client.get(
        f"/trades/leader/{test_db['leader'].id}?instrument_type=OPTION",
        headers={"Authorization": f"Bearer {create_test_token(test_db['member'])}"}
    )
    assert response.status_code == 200
    trades = response.json()
    assert len(trades) == 1
    assert trades[0]["symbol"] == "NIFTY23D14800CE"

    # Test unauthorized access
    unauthorized_user = User(email="unauthorized@test.com", hashed_password="testpass")
    response = await test_client.get(
        f"/trades/leader/{test_db['leader'].id}",
        headers={"Authorization": f"Bearer {create_test_token(unauthorized_user)}"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_websocket_connection():
    client_id = "test_client"
    uri = f"ws://localhost:8000/trades/ws/{client_id}"
    
    async with websockets.connect(uri) as websocket:
        # Test connection is established
        assert websocket.open
        
        # Send a test message
        test_message = json.dumps({"type": "test"})
        await websocket.send(test_message)
        
        # Verify connection is closed properly
        await websocket.close()
        assert websocket.closed

def create_test_token(user: User) -> str:
    # Implement token creation for testing
    # This should match your actual token creation logic
    return "test_token" 