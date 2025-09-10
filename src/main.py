import asyncio
import websockets
import json

# Placeholder for user connections
connections = set()

async def handle_connection(websocket, path):
    try:
        connections.add(websocket)
        print(f"Client connected: {websocket.remote_address}")

        async def send_message(ws, message):
            await ws.send(json.dumps({"type": "chat", "message": message}))

        async def receive_message(ws):
            try:
                message = await ws.recv()
                print(f"Received from {websocket.remote_address}: {message}")
                # Broadcast the message to all connected clients
                for connection in connections:
                    await send_message(connection, message)
            except Exception as e:
                print(f"Error receiving from {websocket.remote_address}: {e}")
                # Clean up the connection
                connections.remove(websocket)
                await websocket.close()

        # Handle receiving messages from the client
        await receive_message(websocket)

    except Exception as e:
        print(f"Error in connection: {e}")
        # Clean up the connection
        if websocket in connections:
            connections.remove(websocket)
            await websocket.close()

# Example function to start the server
async def start_server():
    await websockets.serve(handle_connection, "localhost", 8765)
    print("Server started at ws://localhost:8765")

# Start the server
async def main():
    await start_server()

if __name__ == "__main__":
    asyncio.run(main())