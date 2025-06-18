import asyncio
import websockets
import json
import httpx
from datetime import date
from urllib.parse import urlencode

async def test_trade_history():
    # We'll test with leader_id=1 first, if it fails we can try other IDs
    leader_id = 1
    token = "BxTtnQgygRSFTTc6R5CEIyYdg0I800BX"
    
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test getting all trades
            print(f"\nTesting GET {base_url}/trades/leader/{leader_id}")
            response = await client.get(
                f"{base_url}/trades/leader/{leader_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Status Code: {response.status_code}")
            print("Response:")
            print(json.dumps(response.json() if response.status_code == 200 else response.text, indent=2))
            
            if response.status_code == 404:
                # Try with leader_id=2 if first attempt fails
                leader_id = 2
                print(f"\nRetrying with leader_id={leader_id}")
                response = await client.get(
                    f"{base_url}/trades/leader/{leader_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"Status Code: {response.status_code}")
                print("Response:")
                print(json.dumps(response.json() if response.status_code == 200 else response.text, indent=2))
            
            if response.status_code == 200:
                # Only continue with filters if we got a successful response
                # Test filtering by instrument type
                print("\nTesting OPTION filter")
                response = await client.get(
                    f"{base_url}/trades/leader/{leader_id}?instrument_type=OPTION",
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"Status Code: {response.status_code}")
                print("Response:")
                print(json.dumps(response.json() if response.status_code == 200 else response.text, indent=2))
                
                # Test filtering by date and status
                print("\nTesting date and status filters")
                params = {
                    "start_date": date.today().isoformat(),
                    "end_date": date.today().isoformat(),
                    "status": "COMPLETE"
                }
                response = await client.get(
                    f"{base_url}/trades/leader/{leader_id}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"Status Code: {response.status_code}")
                print("Response:")
                print(json.dumps(response.json() if response.status_code == 200 else response.text, indent=2))
        
        except httpx.ConnectError:
            print("\nError: Could not connect to the server. Make sure the FastAPI server is running (uvicorn app.main:app --reload)")
        except Exception as e:
            print(f"\nError: {str(e)}")

async def test_websocket():
    client_id = "test_client_1"
    token = "BxTtnQgygRSFTTc6R5CEIyYdg0I800BX"
    query_params = urlencode({"token": token})
    uri = f"ws://localhost:8001/trades/ws/{client_id}?{query_params}"
    
    try:
        print(f"\nConnecting to WebSocket at: {uri}")
        async with websockets.connect(uri) as websocket:
            print(f"WebSocket connected with client_id: {client_id}")
            
            # Keep connection open for 30 seconds to receive any updates
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    print(f"Received message: {message}")
            except asyncio.TimeoutError:
                print("No messages received in 30 seconds")
            except Exception as e:
                print(f"Error during message reception: {e}")
    except ConnectionRefusedError:
        print("\nError: Could not connect to WebSocket. Make sure the FastAPI server is running.")
    except Exception as e:
        print(f"\nWebSocket Error: {str(e)}")

async def main():
    print("Testing Trade History API...")
    await test_trade_history()
    
    print("\nTesting WebSocket Connection...")
    await test_websocket()

if __name__ == "__main__":
    asyncio.run(main()) 