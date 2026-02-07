import pytesseract
from PIL import Image, ImageDraw, ImageFont
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
from collections import deque
from datetime import datetime

hotkey = 'f10'
exit_hotkey = 'f12'
monitor_idx = 0

# client = OpenAI()

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
overlay_image_global = ""
overlay_boxes_global = []
image_size_global = (0, 0)
capture_history = deque(maxlen=50)
capture_counter = 0

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
    global overlay_image_global
    global overlay_boxes_global
    global image_size_global
    global capture_history
    global capture_counter
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
            image_size_global = (img.width, img.height)

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

            # Build a newline string for display and render an overlay with boxes + text.
            extracted_lines = []
            for item in extracted_text:
                if not isinstance(item, dict):
                    continue
                text_val = item.get("text")
                if text_val is None:
                    continue
                text_str = text_val if isinstance(text_val, str) else str(text_val)
                if text_str:
                    extracted_lines.append(text_str)
            extracted_text_global = "\n".join(extracted_lines) if extracted_lines else str(extracted_text)

            def build_overlay_boxes(ocr_results):
                boxes = []
                for item in ocr_results or []:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text")
                    polygon = item.get("position")
                    if text is None or polygon is None:
                        continue

                    text_str = text if isinstance(text, str) else str(text)

                    try:
                        points = [tuple(p) for p in polygon]
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        min_x, max_x = min(xs), max(xs)
                        min_y, max_y = min(ys), max(ys)
                    except Exception:
                        continue

                    boxes.append({
                        "text": text_str,
                        "left": int(min_x),
                        "top": int(min_y),
                        "width": int(max_x - min_x),
                        "height": int(max_y - min_y)
                    })
                return boxes

            overlay_boxes_global = build_overlay_boxes(extracted_text)
            print(f"Extracted Text: {extracted_text}")

            capture_counter += 1
            capture_history.appendleft({
                "id": capture_counter,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "image": image_global,
                "overlay_boxes": overlay_boxes_global,
                "image_width": image_size_global[0],
                "image_height": image_size_global[1],
                "extracted_text": extracted_text_global,
                "translated_text": translated_text_global,
            })

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
        <style>
            .overlay-container {
                position: relative;
                width: {{ image_width }};
                height: {{ image_height }};
                background-image: url('{{ image }}');
                background-size: 100% 100%;
                background-repeat: no-repeat;
                border: 1px solid #ddd;
            }
            .overlay-text {
                position: absolute;
                color: red;
                font-size: 16px;
                line-height: 1.2;
                white-space: pre-wrap;
                padding: 0;
                margin: 0;
            }
            .history-item {
                border: 1px solid #ccc;
                padding: 8px;
                margin-bottom: 12px;
            }
            .history-image {
                position: relative;
                border: 1px solid #eee;
                margin-top: 6px;
                overflow: hidden;
            }
        </style>
        <body>
            <h1>Extracted Text</h1>
            <pre>{{ extracted_text }}</pre>
        </body>
        <body>
            <h1>Translated Text</h1>
            <pre>{{ translated_text }}</pre>
        </body>
        <body>
            <h1>Overlay (Selectable Text)</h1>
            <div class="overlay-container">
                {% for box in overlay_boxes %}
                    <div class="overlay-text" style="left: {{ box.left }}px; top: {{ box.top }}px; width: {{ box.width }}px; height: {{ box.height }}px;">{{ box.text }}</div>
                {% endfor %}
            </div>
        </body>
        <img src="{{ image }}" width="854" height="460"/>

        <body>
            <h1>History (Last {{ history|length }} captures, max 50)</h1>
            {% for item in history %}
                <div class="history-item">
                    <div><strong>#{{ item.id }}</strong> — {{ item.timestamp }}</div>
                    <div>Extracted:</div>
                    <pre>{{ item.extracted_text }}</pre>
                    <div class="history-image" style="width: {{ item.image_width }}px; height: {{ item.image_height }}px; background-image: url('{{ item.image }}'); background-size: 100% 100%; background-repeat: no-repeat;">
                        {% for box in item.overlay_boxes %}
                            <div class="overlay-text" style="left: {{ box.left }}px; top: {{ box.top }}px; width: {{ box.width }}px; height: {{ box.height }}px;">{{ box.text }}</div>
                        {% endfor %}
                    </div>
                </div>
            {% endfor %}
        </body>
    </html>
    ''', translated_text=translated_text_global, extracted_text=extracted_text_global, image=image_global, overlay_image=overlay_image_global, overlay_boxes=overlay_boxes_global, image_width=f"{image_size_global[0]}px", image_height=f"{image_size_global[1]}px", history=list(capture_history))

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
