import pytesseract
from PIL import Image
import keyboard
# from googletrans import Translator
from mss import mss
from screeninfo import get_monitors
from flask import Flask, render_template_string
from flask_socketio import SocketIO
import threading
import openai
import io
import base64
from openai import OpenAI
from cnocr import CnOcr

hotkey = 'ctrl+f3'
exit_hotkey = 'f12'
monitor_idx = 1

client = OpenAI()

# Ensure Tesseract is installed and the path is configured (update with your path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# cnocr
ocr = CnOcr()

# Initialize translator
# translator = Translator()

# Flask app initialization
app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')

# Global variable to store translated text
translated_text_global = ""
extracted_text_global = ""
image_global = ""

def get_monitor(idx):
    # Get a list of connected monitors
    monitors = get_monitors()
    if len(monitors) > idx:
        # Return the monitor's info
        return monitors[idx]
    else:
        raise Exception("Monitor not found")

def capture_screen_second_monitor():
    global translated_text_global
    global extracted_text_global 
    global image_global
    try:
        # Get the selected monitor details
        selected_monitor = get_monitor(monitor_idx)

        # Define the region to capture (only the selected monitor)
        left = selected_monitor.x
        top = selected_monitor.y
        width = selected_monitor.width
        height = selected_monitor.height

        # Capture the screen using mss
        with mss() as sct:
            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            screenshot = sct.grab(monitor)

            # Convert the raw screenshot to a PIL Image
            img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
            # img.show()

            # Save the image to a BytesIO object (in-memory file)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')  # Save as PNG or any other format

            # Get the binary data from the BytesIO object and encode it in base64
            img_bytes.seek(0)  # Go to the start of the BytesIO object
            # base64_img = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            base64_img = base64.b64encode(img_bytes.read()).decode('utf-8')
            image_global = f"data:image/png;base64,{base64_img}"

            # response = client.chat.completions.create(
            #     model="gpt-4o",
            #     messages=[
            #         {
            #             "role": "user",
            #             "content": [
            #                 {"type": "text", "text": "Extract the Chinese text in the image"},
            #                 {
            #                     "type": "image_url",
            #                     "image_url": {
            #                         "url": image_global
            #                     }
            #                 },
            #             ],
            #         }
            #     ],
            #     temperature=0.1,
            #     max_tokens=300,
            # )
            # extracted_text = response.choices[0].message.content

            # Perform OCR to extract text
            # extracted_text = pytesseract.image_to_string(img, lang='chi_sim')

            extracted_text = ocr.ocr(img)

            extracted_text_global = extracted_text
            print(f"Extracted Text: {extracted_text}")

            # Emit a message to the client to refresh the page
            socketio.send({'data': 'Refresh the page'}, namespace='/')
            socketio.emit('refresh', {'data': 'Refresh the page'}, namespace='/')

            # Translate the extracted text using Google Translate
            # if extracted_text.strip():  # Check if there's any text to translate
            #     translated_text_global = translator.translate(extracted_text, src='zh-cn' dest='en').text
            #     print(f"Translated Text: {translated_text_global}")

            #     # Emit a message to the client to refresh the page
            #     socketio.emit('refresh', {'data': 'Refresh the page'})
            # else:
            #     print("No text found to translate.")
    except Exception as e:
        print(f"Error: {str(e)}")

def on_hotkey_pressed():
    global extracted_text_global
    print("Hotkey pressed! Capturing the screen on second monitor...")
    extracted_text_global = "loading..."
    socketio.send({'data': 'Refresh the page'}, namespace='/')
    socketio.emit('refresh', {'data': 'Refresh the page'}, namespace='/')
    capture_screen_second_monitor()

# Flask route to display translated text
@app.route('/')
def show_translated_text():
    return render_template_string('''
    <html>
        <head>
            <title>Translated Text</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
             <script type="text/javascript">
                // Establish WebSocket connection with the server
                var socket = io();
                console.log("Socket connected");

                socket.onAny((eventName, ...args) => {
                    console.log(eventName);
                });


                // Listen for the "refresh" message
                socket.on('refresh', function (msg) {
                    console.log('Refreshing page...');
                    window.location.reload();  // Refresh the page
                });

                // Test the connection
                socket.on('connect', function() {
                    console.log('WebSocket connected!');
                });

                socket.on('disconnect', function() {
                    console.log('WebSocket disconnected');
                });
            </script>
        </head>
        <body>
            <h1>Extracted Text</h1>
            <pre>{{ extracted_text }}</pre>
        </body>
        <body>
            <h1>Translated Text</h1>
            <pre>{{ translated_text }}</pre>
        </body>
        <img src={{ image }} width="854" height="460"/>
    </html>
    ''', translated_text=translated_text_global, extracted_text=extracted_text_global, image=image_global)

# Run the Flask app in a separate thread
def run_flask_app():
    socketio.run(app, port=5000)

# Start the Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

# Set up hotkey to capture the screen on "Ctrl+Shift+S"
keyboard.add_hotkey(hotkey, on_hotkey_pressed)

# Keep the program running to listen for the hotkey press
print(f"Press {hotkey} to capture the second monitor screen and translate...")
print("Open http://localhost:5000 in your browser to see the translated text.")
keyboard.wait(exit_hotkey)  # Press ESC to quit the program
