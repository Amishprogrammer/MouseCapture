import asyncio
import os
import pytesseract
import pyautogui
import pyperclip
import cv2
import numpy as np
from PIL import ImageGrab
import tkinter as tk
import keyboard
import threading
from tkinter import ttk
import webbrowser
import re
import requests
from io import BytesIO
import httpx
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Set up pytesseract path (update this based on your installation)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Dictionary of target words and their corresponding predefined terms
TARGET_WORDS = {
    "Name": "Amish Singh",
    "First Name": "Amish",
    "Last Name": "Singh",
    "Full Name": "Amish Singh",
    "Email": "amishsingh1210@gmail.com",
    "Email Address": "amishsingh1210@gmail.com",
    "E-mail": "amishsingh1210@gmail.com",
    "Phone Number": "7002780696",
    "Mobile Number": "7002780696",
    "Contact Number": "7002780696"
}

# Variables to control the width and height of the box
BOX_WIDTH_EM = 10  # Width in em
BOX_HEIGHT_EM = 4  # Height in em
app_running = True  # To manage the app's running state

def google_search(query, image_search=False):
    """Search the extracted text on Google or Google Images."""
    if query.strip():
        if image_search:
            search_url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}"
            print(f"Searching Bing Images for: {query}")
        else:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            print(f"Searching Google for: {query}")
        webbrowser.open(search_url)
    else:
        print("No valid text to search.")

def create_transparent_box(root, canvas, clipboard_label):
    """Create a transparent box with a green border around the mouse pointer and update clipboard text."""
    def update_box():
        """Update the position and size of the box."""
        try:
            if not app_running:
                root.destroy()
                return

            # Get mouse position
            x, y = pyautogui.position()

            # Update the position of the rectangle
            canvas.coords(
                "capture_box",
                x - BOX_WIDTH_EM * 16 // 2,
                y - BOX_HEIGHT_EM * 16 // 2,
                x + BOX_WIDTH_EM * 16 // 2,
                y + BOX_HEIGHT_EM * 16 // 2
            )

            # Update the clipboard label position
            canvas.coords(
                "clipboard_label",
                x, y + BOX_HEIGHT_EM * 16 // 2 + 35  # Position below the box
            )

            # Update the clipboard content (truncate if too long)
            clipboard_text = pyperclip.paste()
            truncated_text = clipboard_text[:30] + ("..." if len(clipboard_text) > 30 else "")
            clipboard_label.config(text=f"{truncated_text}", fg="green")

            # Schedule the next update
            root.after(50, update_box)
        except Exception as e:
            print(f"Error in update_box: {e}")

    # Create the transparent box
    canvas.create_rectangle(
        0, 0, 1, 1,  # Initial size, will be updated in `update_box`
        outline="green",
        width=2,
        tags="capture_box"
    )

    # Add clipboard label to canvas
    canvas.create_window(0, 0, window=clipboard_label, tags="clipboard_label")

    # Start updating the box position
    update_box()

def capture_box():
    """Capture a box of specified dimensions around the mouse pointer and return the image."""
    x, y = pyautogui.position()
    box_width = BOX_WIDTH_EM * 16  # Convert em to pixels
    box_height = BOX_HEIGHT_EM * 16  # Convert em to pixels
    left = max(x - box_width // 2, 0)
    top = max(y - box_height // 2, 0)
    right = left + box_width
    bottom = top + box_height
    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
    return screenshot

def find_nearest_text(data):
    """Extract and arrange text from OCR output."""
    words = data['text']
    arranged_text = " ".join(word for word in words if word.strip())
    return arranged_text

def process_image(image):
    """Process the image and perform OCR to extract text."""
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    open_cv_image = cv2.resize(open_cv_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    open_cv_image = cv2.GaussianBlur(open_cv_image, (5, 5), 0)

    try:
        data = pytesseract.image_to_data(open_cv_image, output_type=pytesseract.Output.DICT)
    except Exception as e:
        print(f"Error in OCR processing: {e}")
        data = {'text': [], 'left': [], 'top': [], 'width': [], 'height': []}

    return data


def capture_screenshot(screenshot):
    """Save the captured screenshot to the current working directory."""
    file_path = os.path.join(os.getcwd(), "screenshot.jpg")
    screenshot.save(file_path, "JPEG")
    print(f"Screenshot saved at: {file_path}")
    return file_path
 
FILE_PATH = os.path.join(os.getcwd(), "screenshot.jpg")
GOOGLE_LENS_URL = "https://lens.google.com/upload"
BING_IMAGE_SEARCH_URL = "https://www.bing.com/visualsearch"
def upload_to_google_lens():
    # Automatically install and use the correct ChromeDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)  # Keep browser open
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # Open Bing Visual Search
        driver.get(BING_IMAGE_SEARCH_URL)

        # Wait for Upload Button & Ensure It’s Visible
        upload_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )
        driver.execute_script("arguments[0].style.display = 'block';", upload_button)

        # Upload Screenshot
        upload_button.send_keys(FILE_PATH)
        print("Image uploaded to Bing successfully!")

        # Wait for Image Preview to Load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "visualSearchResults"))
        )
        print("Image processed successfully!")

        # Keep the browser open for manual verification
        print("🔹 Browser will remain open. Close it manually when done.")
        while True:
            time.sleep(1)  # Keep script running

    except Exception as e:
        print(f"❌ Error during upload: {e}")

def translate_text(query):
    """Translate the selected text using Google Translate."""
    if query:
        print(f"Translating: {query}")
        webbrowser.open(f"https://translate.google.com/?sl=auto&tl=en&text={query}&op=translate")

def start_application():
    """Start the main application loop."""
    global app_running
    print("Press 'Ctrl + Shift + A' to activate the box. Press 'Ctrl + Shift + O' to exit.")
    while app_running:
        try:
            if keyboard.is_pressed('ctrl+shift+a'):
                print("Box activated! Capturing...")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)

                if nearest_text:
                    print(f"Nearest Text: {nearest_text}")
                    for key, value in TARGET_WORDS.items():
                        if re.search(r'\b' + re.escape(key) + r'\b', nearest_text, re.IGNORECASE):
                            print(f"Target word '{key}' found! Copying corresponding value to clipboard.")
                            pyperclip.copy(value)
                            print("Copied to clipboard.")
                            break
                else:
                    print("No text detected in the box.")

            if keyboard.is_pressed('ctrl+shift+g'):
                print("Google Search activated!")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)
                google_search(nearest_text)
                
            if keyboard.is_pressed('ctrl+shift+t'):
                print("Translation activated!")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)
                translate_text(nearest_text)

            if keyboard.is_pressed('ctrl+shift+q'):
                print("Image Search activated! Capturing screenshot...")
                # screenshot = capture_box()
                # screenshot_path = save_screenshot_to_directory(screenshot)
                # print("Uploading image to Bing for search...")
                # handle_image_upload(screenshot_path)
                screenshot=capture_box()
                screenshot_path = capture_screenshot(screenshot)
                print("Uploading image for search...")
                upload_to_google_lens()

            if keyboard.is_pressed('ctrl+shift+o'):
                app_running = False
                print("Exiting application.")
                break

        except Exception as e:
            print(f"Error: {e}")

def main():
    def update_box_width(value):
        global BOX_WIDTH_EM
        BOX_WIDTH_EM = int(round(float(value)))
        width_label.config(text=f"Width: {BOX_WIDTH_EM} em")  # Update width label
    def update_box_height(value):
        global BOX_HEIGHT_EM
        BOX_HEIGHT_EM = int(round(float(value)))
        height_label.config(text=f"Height: {BOX_HEIGHT_EM} em")  # Update height label

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")

    canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="white")
    canvas.pack()

    clipboard_label = tk.Label(root, text=f"{pyperclip.paste()[:30]}...", bg="white", fg="black")
    create_transparent_box(root, canvas, clipboard_label)

    # Labels to display slider values
    width_label = tk.Label(root, text=f"Width: {BOX_WIDTH_EM} em", bg="white", fg="black")
    height_label = tk.Label(root, text=f"Height: {BOX_HEIGHT_EM} em", bg="white", fg="black")

    # Position labels on the screen
    width_label.place(x=root.winfo_screenwidth() - 250, y=78)
    height_label.place(x=root.winfo_screenwidth() - 250, y=228)

    slider_width = ttk.Scale(root, from_=1, to=50, orient=tk.VERTICAL, command=update_box_width)
    slider_width.set(BOX_WIDTH_EM)
    slider_width.place(x=root.winfo_screenwidth() - 200, y=100)

    slider_height = ttk.Scale(root, from_=1, to=20, orient=tk.VERTICAL, command=update_box_height)
    slider_height.set(BOX_HEIGHT_EM)
    slider_height.place(x=root.winfo_screenwidth() - 200, y=250)

    app_thread = threading.Thread(target=start_application, daemon=True)
    app_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()
