import pytesseract
from PIL import Image
import keyboard
from googletrans import Translator
import io
import time
from mss import mss
from screeninfo import get_monitors
import webbrowser
import tempfile
import os

# Ensure Tesseract is installed and the path is configured (update with your path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize translator
translator = Translator()

def get_second_monitor():
    # Get a list of connected monitors
    monitors = get_monitors()
    if len(monitors) > 1:
        # Return the second monitor's info
        return monitors[1]
    else:
        raise Exception("Second monitor not found")

def open_text_in_browser(text):
    # Create a temporary HTML file
    html_content = f"""
    <html>
    <head><title>Translated Text</title></head>
    <body>
    <h1>Extracted and Translated Text</h1>
    <pre>{text}</pre>
    </body>
    </html>
    """

    # Write the content to a temporary file
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
        f.write(html_content)
        temp_file_path = f.name

    # Open the temporary file in the default web browser
    file = f"file://{temp_file_path}"
    print(temp_file_path)
    firefoxPath = "C:/Program Files/Mozilla Firefox/firefox.exe %s"
    webbrowser.get(firefoxPath).open(file)
    # webbrowser.open(file)

def capture_screen_second_monitor():
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

            # Display the screenshot
            # img.show()

            # Perform OCR to extract text
            extracted_text = pytesseract.image_to_string(img, lang='chi_sim')
            print(f"Extracted Text: {extracted_text}")

            open_text_in_browser(extracted_text)
            # # Translate the extracted text using Google Translate
            # if extracted_text.strip():  # Check if there's any text to translate
            #     translated_text = translator.translate(extracted_text, src='zh-cn', dest='en').text
            #     print(f"Translated Text: {translated_text}")
            # else:
            #     print("No text found to translate.")

    except Exception as e:
        print(f"Error: {str(e)}")

def on_hotkey_pressed():
    print("Hotkey pressed! Capturing the screen on second monitor...")
    capture_screen_second_monitor()

# Set up hotkey to capture the screen on "Ctrl+Shift+S"
hotkey = 'ctrl+f3'
keyboard.add_hotkey(hotkey, on_hotkey_pressed)

# Keep the program running to listen for the hotkey press
print(f"Press {hotkey} to capture the second monitor screen and translate...")
keyboard.wait('esc')  # Press ESC to quit the program
