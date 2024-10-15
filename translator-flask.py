import pytesseract
from PIL import Image
import keyboard
from googletrans import Translator
from mss import mss
from screeninfo import get_monitors
from flask import Flask, render_template_string
import threading

# Ensure Tesseract is installed and the path is configured (update with your path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize translator
translator = Translator()

# Flask app initialization
app = Flask(__name__)

# Global variable to store translated text
translated_text_global = ""
extracted_text_global = ""

def get_second_monitor():
    # Get a list of connected monitors
    monitors = get_monitors()
    if len(monitors) > 1:
        # Return the second monitor's info
        return monitors[1]
    else:
        raise Exception("Second monitor not found")

def capture_screen_second_monitor():
    global translated_text_global
    global extracted_text_global 
    try:
        # Get the second monitor details
        second_monitor = get_second_monitor()

        # Define the region to capture (only the second monitor)
        left = second_monitor.x
        top = second_monitor.y
        width = second_monitor.width
        height = second_monitor.height

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

            # Perform OCR to extract text
            extracted_text = pytesseract.image_to_string(img, lang='chi_sim')
            extracted_text_global = extracted_text
            print(f"Extracted Text: {extracted_text_global}")

            # Translate the extracted text using Google Translate
            if extracted_text.strip():  # Check if there's any text to translate
                translated_text_global = translator.translate(extracted_text, src='zh-cn', dest='en').text
                extracted_text_global = extracted_text
                print(f"Translated Text: {translated_text_global}")
            else:
                print("No text found to translate.")
    except Exception as e:
        print(f"Error: {str(e)}")

def on_hotkey_pressed():
    print("Hotkey pressed! Capturing the screen on second monitor...")
    capture_screen_second_monitor()

# Flask route to display translated text
@app.route('/')
def show_translated_text():
    print(extracted_text_global)
    return render_template_string('''
    <html>
        <head><title>Translated Text</title></head>
        <body>
            <h1>Extracted and Translated Text</h1>
            <pre>{{ translated_text }}</pre>
        </body>
    </html>
    ''', translated_text=extracted_text_global)

# Run the Flask app in a separate thread
def run_flask_app():
    app.run(port=5000)

# Start the Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

# Set up hotkey to capture the screen on "Ctrl+Shift+S"
hotkey = 'ctrl+f3'
keyboard.add_hotkey(hotkey, on_hotkey_pressed)

# Keep the program running to listen for the hotkey press
print(f"Press {hotkey} to capture the second monitor screen and translate...")
print("Open http://localhost:5000 in your browser to see the translated text.")
keyboard.wait('f12')  # Press ESC to quit the program