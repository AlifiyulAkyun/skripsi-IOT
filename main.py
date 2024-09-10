import asyncio
import traceback
from datetime import datetime

import websockets
from PIL import Image
import io
import json
import paho.mqtt.client as mqtt
import mysql.connector

counter: int = 0

# Fungsi untuk menyimpan data ke database
def insert_into_db(cursor, conn, status, label, confident, time):
    # Menyisipkan data ke dalam tabel
    insert_query = "INSERT INTO data (status, label, confident, time) VALUES (%s, %s, %s, %s)"
    cursor.execute(insert_query, (status, label, confident, time))
    # Commit perubahan setelah setiap insert
    conn.commit()

# Callback yang akan dipanggil ketika terhubung ke broker MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))

# Callback yang akan dipanggil ketika menerima pesan dari broker MQTT
def on_message(client, userdata, msg):
    try:
        print(msg.topic + " " + str(msg.payload))

        # Mengubah byte string menjadi string biasa
        json_string = msg.payload.decode('utf-8')

        # Mengubah string JSON menjadi dictionary Python
        data = json.loads(json_string)

        # Menampilkan hasil deserialisasi
        print(data)

        # Mengakses elemen tertentu dalam dictionary jika diperlukan
        status = data.get('status')
        label = data.get('label')
        confident = data.get('confident')
        time = data.get('time')

        # Insert data ke database
        insert_into_db(userdata['cursor'], userdata['conn'], status, label, confident, time)

    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")

    except Exception as e:
        print(f"Error: {e}")

# Fungsi callback untuk menghandle pesan masuk dari WebSocket
async def handle_websocket(websocket, path):
    global counter
    try:
        while True:
            message = await websocket.recv()
            print(f"type data: {type(message)}")
            if isinstance(message, bytes):
                try:
                    print("image received")
                    image = Image.open(io.BytesIO(message))
                    counter += 1
                    file_name = "{}".format(f"{counter:06}")
                    print(f"file name: {file_name}.jpg")
                    image.save("images/" + file_name + ".jpg")

                    # Create a JSON response
                    response_message = {
                        "status": "success",
                        "label": "uwais",
                        "confident": 100
                    }
                    response_json = json.dumps(response_message)

                    # Send the JSON response back to the client
                    await websocket.send(response_json)
                    print("Response sent to client")

                    # Insert data into the database
                    insert_into_db(cursor, conn, response_message['status'], 
                                   response_message['label'], 
                                   response_message['confident'], 
                                   datetime.now())

                except Exception as e:
                    traceback.print_exc()
            else:
                print(f"Received message: {message}")
            # Anda dapat mengirimkan respons kembali ke client jika diperlukan
    except websockets.ConnectionClosed:
        pass

if __name__ == "__main__":
    # Koneksi ke database MySQL
    try:
        conn = mysql.connector.connect(
            host="34.127.108.239",
            user="root",
            password="12345",
            database="dbface"
        )
        cursor = conn.cursor()
        print("Database connection successful")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        exit(1)  # Exit the script if the database connection fails

    # Inisialisasi client MQTT
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    # Set username dan password untuk autentikasi MQTT
    mqtt_client.username_pw_set("uwais", "uw415_4Lqarn1")

    # Pass cursor and connection to MQTT userdata
    mqtt_client.user_data_set({'cursor': cursor, 'conn': conn})

    # Hubungkan ke broker MQTT
    mqtt_client.connect("broker.sinaungoding.com", 1883, 60)  # Ganti dengan alamat broker MQTT Anda

    # Subscribe ke topik yang diinginkan
    mqtt_client.subscribe("esp32/json_output")

    # Mulai loop MQTT dalam thread terpisah
    mqtt_client.loop_start()

    # Memulai server WebSocket
    start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Disconnecting...")

        # Menutup koneksi saat program berakhir
    cursor.close()
    conn.close()
