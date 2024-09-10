import asyncio
import websockets


async def send_image(uri, image_path):
    async with websockets.connect(uri) as websocket:
        with open(image_path, "rb") as image_file:
            # Read the image file as bytes
            image_bytes = image_file.read()

            # Send the byte array of the image
            await websocket.send(image_bytes)
            print(f"Image sent: {image_path}")

            # Receive the response from the server
            response = await websocket.recv()
            print(f"Response from server: {response}")


# WebSocket server URI
uri = "ws://localhost:8765"

# Path to the image file
image_path = "images_test/image1.jpeg"
# image_path = "images_test/image2.jpeg"
# image_path = "images_test/image3.jpeg"
# image_path = "images_test/image4.jpeg"
# image_path = "images_test/image5.jpeg"

# Run the send_image function
asyncio.get_event_loop().run_until_complete(send_image(uri, image_path))