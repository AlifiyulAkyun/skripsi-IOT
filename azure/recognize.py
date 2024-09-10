import asyncio
import traceback

import websockets
from PIL import Image
import io

import tensorflow as tf
import numpy as np
from datetime import datetime
import json

from mtcnn.mtcnn import MTCNN

class_names = ['Anjani Dwi Lestari', 'Ahmad Rafif Alaudin', 'Alifiyul Akyun', 'Amelia Marshanda',
               'Ananda Ayu Sekar', 'Anisa Fitri', 'Auryno Nagata', 'Daffa Satya', 'Irma Maulidia',
               'Muhamad Alif Rizki', 'Novianawati', 'Nurlaily Asrobika', 'Reynaldi Fakhri',
               'Rini Saqila', 'Rofika Nur Aini', 'Rofiqoh Wahyuningtyas', 'Shintya Rahmawati',
               'Tika Rahmawati', 'Tutik Sundari', 'Tzelginia Putri']
batch_size = 32
img_height = 100
img_width = 100

model = tf.keras.models.load_model("model.h5")
print("Model loaded")


def detect_faces(image):
    image_array = np.array(image)

    # Create an MTCNN detector
    detector = MTCNN()

    # Detect faces
    faces = detector.detect_faces(image_array)
    # Iterate over each detected face
    for i, face in enumerate(faces):
        # Get the bounding box coordinates
        x, y, width, height = face['box']

        # Ensure the bounding box is square
        size = max(width, height)
        center_x = x + width // 2
        center_y = y + height // 2

        # Calculate new coordinates to ensure the box is square
        x_new = max(center_x - size // 2, 0)
        y_new = max(center_y - size // 2, 0)

        # Ensure the new bounding box doesn't exceed image dimensions
        x_new = min(x_new, image_array.shape[1] - size)
        y_new = min(y_new, image_array.shape[0] - size)

        # Extract the face from the image
        face_image = image_array[y_new:y_new + size, x_new:x_new + size]

        # Convert face_image array back to image
        face_image_pil = Image.fromarray(face_image)
        print(face_image_pil)
        return face_image_pil


# Fungsi callback untuk menghandle pesan masuk dari WebSocket
async def handle_websocket(websocket, path):
    try:
        while True:
            message = await websocket.recv()
            print(f"type data: {type(message)}")
            if isinstance(message, bytes):
                try:
                    start_time = datetime.now()
                    print("image received")
                    image = Image.open(io.BytesIO(message))
                    face_image = detect_faces(image)
                    face_image = face_image.resize((img_width, img_height))
                    print(face_image.size)
                    img_array = tf.keras.preprocessing.image.img_to_array(face_image)
                    img_array = np.expand_dims(img_array, axis=0)  # Create a batch
                    img_array = img_array / 255.0  # Rescale image if you used rescaling during training

                    predict = model.predict(img_array, batch_size=batch_size)
                    score = tf.nn.softmax(predict[0])

                    predicted_class_index = np.argmax(predict, axis=1)
                    predicted_class_label = class_names[predicted_class_index[0]]

                    confident = format(100 * np.max(score), ".2f")
                    print("This image {} {} %".format(predicted_class_label, confident))
                    end_time = datetime.now()
                    print('Duration: {}'.format(end_time - start_time))

                    # Create a JSON response
                    response_message = {
                        "status": "success",
                        "label": predicted_class_label,
                        "confident": confident
                        
                    }
                    response_json = json.dumps(response_message)

                    # Send the JSON response back to the client
                    await websocket.send(response_json)
                    print("Response sent to client")
                except Exception as e:
                    traceback.print_exc()
            else:
                print(f"Received message: {message}")
            # Anda dapat mengirimkan respons kembali ke client jika diperlukan
            # response = f"Received: {message}"
            # await websocket.send(response)
    except websockets.ConnectionClosed:
        pass


if __name__ == "__main__":
    # Memulai server WebSocket
    start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()