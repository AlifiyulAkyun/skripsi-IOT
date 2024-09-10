import asyncio
import traceback
import websockets
from PIL import Image
import io
import json
import paho.mqtt.client as mqtt
import psycopg2
import tensorflow as tf
import numpy as np
from datetime import datetime
from mtcnn.mtcnn import MTCNN

# Global variables
counter = 0
class_names = ['Anjani Dwi Lestari', 'Ahmad Rafif Alaudin', 'Alifiyul Akyun', 'Amelia Marshanda',
               'Ananda Ayu Sekar', 'Anisa Fitri', 'Auryno Nagata', 'Daffa Satya', 'Irma Maulidia',
               'Muhamad Alif Rizki', 'Novianawati', 'Nurlaily Asrobika', 'Reynaldi Fakhri',
               'Rini Saqila', 'Rofika Nur Aini', 'Rofiqoh Wahyuningtyas', 'Shintya Rahmawati',
               'Tika Rahmawati', 'Tutik Sundari', 'Tzelginia Putri']
batch_size = 32
img_height = 100
img_width = 100

# Load the model
model = tf.keras.models.load_model("model.h5")
print("Model loaded")

# Database connection
conn = psycopg2.connect("postgres://postgres.dzlwczpophxcdqrnqvue:Skripsiface123@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres")
cursor = conn.cursor()

# Function to insert data into the database
def insert_into_db(status, label, confident, datetime_str):
    try:
        insert_query = "INSERT INTO presensi (status, label, confident, datetime) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (status, label, confident, datetime_str))
        conn.commit()
        print("Data berhasil disimpan ke database")
    except psycopg2.Error as e:
        print(f"Error saat menyimpan data ke database: {e}")
        conn.rollback()

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))

def on_message(client, userdata, msg):
    try:
        print(msg.topic + " " + str(msg.payload))
        json_string = msg.payload.decode('utf-8')
        data = json.loads(json_string)
        print(data)

        status = data.get('status')
        label = data.get('label')
        confident = data.get('confident')
        datetime_str = data.get('datetime')

        if not datetime_str:
            datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        insert_into_db(status, label, confident, datetime_str)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Face detection function
def detect_faces(image):
    image_array = np.array(image)
    detector = MTCNN()
    faces = detector.detect_faces(image_array)
    for i, face in enumerate(faces):
        x, y, width, height = face['box']
        size = max(width, height)
        center_x = x + width // 2
        center_y = y + height // 2
        x_new = max(center_x - size // 2, 0)
        y_new = max(center_y - size // 2, 0)
        x_new = min(x_new, image_array.shape[1] - size)
        y_new = min(y_new, image_array.shape[0] - size)
        face_image = image_array[y_new:y_new + size, x_new:x_new + size]
        face_image_pil = Image.fromarray(face_image)
        return face_image_pil

# WebSocket handler
async def handle_websocket(websocket, path):
    global counter
    try:
        while True:
            message = await websocket.recv()
            if isinstance(message, bytes):
                try:
                    start_time = datetime.now()
                    print("Image received")
                    image = Image.open(io.BytesIO(message))
                    
                    # Save the image
                    counter += 1
                    file_name = f"{counter:06}"
                    image.save(f"images/{file_name}.jpg")
                    
                    face_image = detect_faces(image)
                    face_image = face_image.resize((img_width, img_height))
                    img_array = tf.keras.preprocessing.image.img_to_array(face_image)
                    img_array = np.expand_dims(img_array, axis=0)
                    img_array = img_array / 255.0

                    predict = model.predict(img_array, batch_size=batch_size)
                    score = tf.nn.softmax(predict[0])

                    predicted_class_index = np.argmax(predict, axis=1)
                    predicted_class_label = class_names[predicted_class_index[0]]

                    confident = format(100 * np.max(score), ".2f")
                    end_time = datetime.now()
                    duration = end_time - start_time

                    response_message = {
                        "status": "success",
                        "label": predicted_class_label,
                        "confident": confident,
                        "time": end_time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    response_json = json.dumps(response_message)

                    # Insert data into the database
                    insert_into_db(response_message["status"], response_message["label"], 
                                   response_message["confident"], response_message["time"])

                    # Send the JSON response back to the client
                    await websocket.send(response_json)
                    print(f"Response sent to client: {response_json}")
                    print(f"Duration: {duration}")
                except Exception as e:
                    traceback.print_exc()
            else:
                print(f"Received message: {message}")
    except websockets.ConnectionClosed:
        pass

if __name__ == "__main__":
    # Initialize MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    # Set MQTT credentials
    mqtt_client.username_pw_set("uwais", "uw415_4Lqarn1")

    # Connect to MQTT broker
    mqtt_client.connect("broker.sinaungoding.com", 1883, 60)

    # Subscribe to MQTT topic
    mqtt_client.subscribe("esp32/json_output")

    # Start MQTT loop in a separate thread
    mqtt_client.loop_start()

    # Start WebSocket server
    start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)
    
    # Run the event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Disconnecting...")
    finally:
        # Close connections
        cursor.close()
        conn.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()