# Standard Library
import os
import json
import time
import asyncio
from io import BytesIO

# Third-Party Libraries
import pytesseract
import pyautogui
import pyperclip
import cv2
import numpy as np
from PIL import ImageGrab
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import webbrowser
import re
import requests
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import keyboard
import threading

# Your Modules (if any)
from codelibrary import CODE_WORDS  # Make sure this is in the same directory or accessible

# Set up pytesseract path (update this based on your installation)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Dictionary of target words and their corresponding predefined terms
from codelibrary import CODE_WORDS
TARGET_WORDS_FILE = "target_words.json"  # Name of the file to store the data

# print(TARGET_WORDS.keys())
# Variables to control the width and height of the box
BOX_WIDTH_EM = 10  # Width in em
BOX_HEIGHT_EM = 4  # Height in em
app_running = True  # To manage the app's running state
def load_target_words():
    """Loads TARGET_WORDS from the JSON file."""
    try:
        with open(TARGET_WORDS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
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

def save_target_words():
    """Saves TARGET_WORDS to the JSON file."""
    with open(TARGET_WORDS_FILE, "w") as f:
        json.dump(TARGET_WORDS, f, indent=4)

def edit_target_words(root):
    """Opens a new window to edit the TARGET_WORDS dictionary."""

    def add_word():
        new_key = simpledialog.askstring("Add Word", "Enter the target word:")
        if new_key:
            new_value = simpledialog.askstring("Add Value", f"Enter the value for '{new_key}':")
            if new_value:
                TARGET_WORDS[new_key] = new_value
                update_listbox()

    def delete_word():
        selected_index = listbox.curselection()
        if selected_index:
            key = listbox.get(selected_index)
            del TARGET_WORDS[key]
            update_listbox()

    def edit_word():
        selected_index = listbox.curselection()
        if selected_index:
            selected_item = listbox.get(selected_index)
            # Extract the key (before the colon)
            key = selected_item.split(":")[0].strip()  # Split and strip whitespace

            new_value = simpledialog.askstring("Edit Value", f"Enter the new value for '{key}':", initialvalue=TARGET_WORDS[key])
            if new_value is not None:
                TARGET_WORDS[key] = new_value
                update_listbox()

    def update_listbox():
        listbox.delete(0, tk.END)
        for key, value in TARGET_WORDS.items():
            listbox.insert(tk.END, f"{key}: {value}")

    def save_and_close():
        save_target_words()  # Save before closing
        edit_window.destroy()

    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Target Words")

    listbox = tk.Listbox(edit_window, width=50)
    listbox.pack(padx=10, pady=10)
    update_listbox()

    add_button = ttk.Button(edit_window, text="Add", command=add_word)
    add_button.pack(pady=5)

    delete_button = ttk.Button(edit_window, text="Delete", command=delete_word)
    delete_button.pack(pady=5)

    edit_button = ttk.Button(edit_window, text="Edit", command=edit_word)
    edit_button.pack(pady=5)
    save_button = ttk.Button(edit_window, text="Save and Close", command=save_and_close)
    save_button.pack(pady=5)
    edit_window.protocol("WM_DELETE_WINDOW", save_and_close)

def get_word_definition(word):
    word = word.split()[0]
    print(word)
    """Get the definition of a word using Free Dictionary API."""
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        print(response)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                definitions = data[0]['meanings'][0]['definitions']
                # Concatenate the definitions into a single string
                concatenated_definitions = " ".join([definition['definition'] for definition in definitions])
                return concatenated_definitions
        return "No definition found"
    except:
        return "Error fetching definition"

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
            root.after(100, update_box)
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

def find_nearest_text(data):
    """Extract and arrange text from OCR output."""
    words = data['text']
    arranged_text = " ".join(word for word in words if word.strip())
    return arranged_text

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
        print("✅ Image uploaded to Bing successfully!")

        # Wait for Image Preview to Load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "visualSearchResults"))
        )
        print("✅ Image processed successfully!")

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

            if keyboard.is_pressed('ctrl+shift+c'):
                print("Box activated! Capturing...")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)
                if nearest_text:
                    print(f"Nearest Text: {nearest_text}")
                    for key, value in CODE_WORDS.items():
                        if re.search(r'\b' + re.escape(key) + r'\b', nearest_text, re.IGNORECASE):
                            print(f"CODE word '{key}' found! Copying corresponding value to clipboard.")
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
            if keyboard.is_pressed('ctrl+shift+m'):
                print("Dictionary activated")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)
                value = get_word_definition(nearest_text)
                pyperclip.copy(value)

            if keyboard.is_pressed('ctrl+shift+t'):
                print("Translation activated!")
                screenshot = capture_box()
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data)
                translate_text(nearest_text)

            if keyboard.is_pressed('ctrl+shift+q'):
                print("Image Search activated! Capturing screenshot...")
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
    global TARGET_WORDS  # Make sure you declare TARGET_WORDS as global in main as well
    TARGET_WORDS = load_target_words()  # Load target words from file
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
    root.attributes("-transparentcolor", root['bg'])

    canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight())
    canvas.pack()

    clipboard_label = tk.Label(root, text=f"{pyperclip.paste()[:30]}...", fg="black")
    create_transparent_box(root, canvas, clipboard_label)

    # Labels to display slider values
    width_label = tk.Label(root, text=f"Width: {BOX_WIDTH_EM} em",  fg="black")
    height_label = tk.Label(root, text=f"Height: {BOX_HEIGHT_EM} em", fg="black")

    # Position labels on the screen
    width_label.place(x=root.winfo_screenwidth() - 250, y=78)
    height_label.place(x=root.winfo_screenwidth() - 250, y=228)

    slider_width = ttk.Scale(root, from_=1, to=root.winfo_screenmmwidth()//2, orient=tk.VERTICAL, command=update_box_width)
    slider_width.set(BOX_WIDTH_EM)
    slider_width.place(x=root.winfo_screenwidth() - 200, y=100)

    slider_height = ttk.Scale(root, from_=1, to=root.winfo_screenmmheight()//2, orient=tk.VERTICAL, command=update_box_height)
    slider_height.set(BOX_HEIGHT_EM)
    slider_height.place(x=root.winfo_screenwidth() - 200, y=250)

    guide = ttk.Label(root, text=f'CTRL+SHIFT+O = Close the application\nCTRL+SHIFT+A = Fetch value from target_words\nCTRL+SHIFT+C = Fetch python code\nCTRL+SHIFT+G = google searching\nCTRL+SHIFT+M = Fetch meaning\nCTRL+SHIFT+T = Translate\nCTRL+SHIFT+Q = Image search',
                  font=("Arial", 7), foreground="green")  # Set text color to green
    guide.place(x=root.winfo_screenwidth() - 250, y=400)

    edit_button = ttk.Button(root, text="Edit Target Words", command=lambda: edit_target_words(root))
    edit_button.place(x=root.winfo_screenwidth() - 250, y=350) 

    app_thread = threading.Thread(target=start_application, daemon=True)
    app_thread.start()
    
    root.protocol("WM_DELETE_WINDOW", save_target_words) # save when user closes the main window using the 'X' button.
    root.mainloop()

if __name__ == "__main__":
    main()


# 
# import pyautogui
# import pytesseract
# import pyperclip
# import cv2
# import numpy as np
# from PIL import ImageGrab
# import tkinter as tk
# import keyboard # type: ignore
# import threading
# from scipy.spatial import distance
# import requests
# import os

# # google search from image
# # google search from image
# # coding algorithms
# # dictionary
# # translation

# # Test if Tesseract path exists
# tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# if os.path.exists(tesseract_path):
#     print("Tesseract is found at:", tesseract_path)
#     pytesseract.pytesseract.tesseract_cmd = tesseract_path
# else:
#     print("Tesseract not found at:", tesseract_path)
#     print("Please verify your installation path")

# # Dictionary of target words and their corresponding predefined terms
# TARGET_WORDS = {
#     # Personal Information
#     "First Name": "Amish",
#     "Last Name": "Singh",
#     "Full Name": "Amish Singh",
#     "Email": "amishsingh1210@gmail.com"
# }

# def create_transparent_box(root, canvas, width, height, clipboard_label):
#     """Create a transparent box with a green border around the mouse pointer and update clipboard text."""
#     def update_box():
#         # Get mouse position
#         x, y = pyautogui.position()

#         # Update the position of the rectangle
#         canvas.coords(
#             "capture_box",
#             x - width // 2,
#             y - height // 2,
#             x + width // 2,
#             y + height // 2
#         )

#         # Update the clipboard label position
#         canvas.coords(
#             "clipboard_label",
#             x, y + height // 2 + 10  # Position below the box
#         )

#         # Update the clipboard content (truncate if too long)
#         clipboard_text = pyperclip.paste()
#         truncated_text = clipboard_text[:30] + ("..." if len(clipboard_text) > 30 else "")
#         clipboard_label.config(text=f"{truncated_text}")

#         # Schedule the next update
#         root.after(50, update_box)

#     # Create the transparent box
#     canvas.create_rectangle(
#         0, 0, width, height,
#         outline="green",
#         width=2,
#         tags="capture_box"
#     )

#     # Add clipboard label to canvas
#     canvas.create_window(0, 0, window=clipboard_label, tags="clipboard_label")

#     # Start updating the box position
#     update_box()

# def capture_box():
#     """Capture a box of 50em x 20em around the mouse pointer and return the image."""
#     x, y = pyautogui.position()
#     box_width = 10 * 16  # 50em in pixels
#     box_height = 4 * 16  # 20em in pixels
#     left = max(x - box_width // 2, 0)
#     top = max(y - box_height // 2, 0)
#     right = left + box_width
#     bottom = top + box_height
#     screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
#     return screenshot

# def process_image(image):
#     """Process the image and perform OCR to extract text with positional information."""
#     open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
#     open_cv_image = cv2.resize(open_cv_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#     open_cv_image = cv2.GaussianBlur(open_cv_image, (5, 5), 0)
#     data = pytesseract.image_to_data(open_cv_image, output_type=pytesseract.Output.DICT)
#     return data

# def find_nearest_text(data, mouse_x, mouse_y, box_left, box_top):
#     """Find the sequence of words closest to the mouse pointer."""
#     words = data['text']
#     positions = zip(data['left'], data['top'], data['width'], data['height'])
#     word_positions = []

#     for word, (x, y, w, h) in zip(words, positions):
#         if word.strip():
#             word_center = ((x + w / 2) + box_left, (y + h / 2) + box_top)
#             word_positions.append((word, word_center))

#     word_positions.sort(key=lambda item: distance.euclidean((mouse_x, mouse_y), item[1]))
#     nearest_text = " ".join([word for word, _ in word_positions[::-1]])
#     return nearest_text

# def get_word_definition(word):
#     """Get the definition of a word using Free Dictionary API."""
#     try:
#         response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
#         if response.status_code == 200:
#             data = response.json()
#             if data and len(data) > 0:
#                 meaning = data[0]['meanings'][0]['definitions'][0]['definition']
#                 return meaning
#         return "No definition found"
#     except:
#         return "Error fetching definition"

# def start_application():
#     """Start the main application loop."""
#     print("Press 'Ctrl + Shift + A' to activate the box for text matching")
#     print("Press 'Ctrl + Shift + D' to look up word definition")
#     print("Press 'Esc' to exit.")

#     while True:
#         try:
#             if keyboard.is_pressed('ctrl+shift+a'):
#                 print("Box activated! Capturing...")
#                 mouse_x, mouse_y = pyautogui.position()
#                 screenshot = capture_box()
#                 box_left, box_top = mouse_x - (50 * 16) // 2, mouse_y - (20 * 16) // 2
#                 data = process_image(screenshot)
#                 nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)

#                 if nearest_text:
#                     print(f"Nearest Text: {nearest_text}")
#                     for key, value in TARGET_WORDS.items():
#                         if key.lower() in nearest_text.lower():
#                             print(f"Target word '{key}' found! Copying corresponding value to clipboard.")
#                             pyperclip.copy(value)
#                             print("Copied to clipboard.")
#                             break
#                             break
#                     else:
#                         print("No target words found near the pointer.")
#                 else:
#                     print("No text detected in the box.")

#                 keyboard.wait('ctrl+shift+a')

#             if keyboard.is_pressed('ctrl+shift+d'):
#                 print("Dictionary lookup activated! Capturing...")
#                 mouse_x, mouse_y = pyautogui.position()
#                 screenshot = capture_box()
#                 box_left, box_top = mouse_x - (50 * 16) // 2, mouse_y - (20 * 16) // 2
#                 data = process_image(screenshot)
#                 nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)

#                 if nearest_text:
#                     # Clean up the text and get the first word
#                     word = nearest_text.strip().split()[0]
#                     print(f"Looking up definition for: {word}")
#                     definition = get_word_definition(word)
#                     pyperclip.copy(definition)
#                     print(f"Definition copied to clipboard: {definition}")
#                 else:
#                     print("No text detected in the box.")

#                 keyboard.wait('ctrl+shift+d')

#             if keyboard.is_pressed('esc'):
#                 print("Exiting application.")
#                 break
#         except Exception as e:
#             print(f"Error: {e}")

# def main():
#     box_width = 10 * 16  # 50em in pixels
#     box_height = 4 * 16  # 20em in pixels

#     root = tk.Tk()
#     root.overrideredirect(True)
#     root.attributes("-topmost", True)
#     root.attributes("-transparentcolor", "white")

#     canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="white")
#     canvas.pack()

#     clipboard_label = tk.Label(root, text=f"{pyperclip.paste()[:30]}...", bg="white", fg="black")
#     create_transparent_box(root, canvas, box_width, box_height, clipboard_label)

#     app_thread = threading.Thread(target=start_application, daemon=True)
#     app_thread.start()

#     root.mainloop()

# if _name_ == "_main_":
#     main()
    
# 

# [
#     {"word":"train",
#     "phonetic":"/tɹeɪn/",
#     "phonetics":[
#         {
#             "text":"/tɹeɪn/",
#             "audio":"https://api.dictionaryapi.dev/media/pronunciations/en/train-1-au.mp3",
#             "sourceUrl":"https://commons.wikimedia.org/w/index.php?curid=45093042",
#             "license":{
#                 "name":"BY-SA 4.0",
#                 "url":"https://creativecommons.org/licenses/by-sa/4.0"
#                 }
#         }
#             ,{"text":"/tɹeɪn/","audio":"https://api.dictionaryapi.dev/media/pronunciations/en/train-1-uk.mp3","sourceUrl":"https://commons.wikimedia.org/w/index.php?curid=9014230","license":{"name":"BY 3.0 US","url":"https://creativecommons.org/licenses/by/3.0/us"}},{"text":"/tɹeɪn/","audio":"https://api.dictionaryapi.dev/media/pronunciations/en/train-1-us.mp3","sourceUrl":"https://commons.wikimedia.org/w/index.php?curid=1197447","license":{"name":"BY-SA 3.0","url":"https://creativecommons.org/licenses/by-sa/3.0"}}],"meanings":[{"partOfSpeech":"noun","definitions":[{"definition":"Elongated portion.","synonyms":[],"antonyms":[]},{"definition":"Connected sequence of people or things.","synonyms":[],"antonyms":[]}],"synonyms":[],"antonyms":[]},{"partOfSpeech":"verb","definitions":[{"definition":"To practice an ability.","synonyms":[],"antonyms":[],"example":"She trained seven hours a day to prepare for the Olympics."},{"definition":"To teach and form (someone) by practice; to educate (someone).","synonyms":[],"antonyms":[],"example":"You can't train a pig to write poetry."},{"definition":"To improve one's fitness.","synonyms":[],"antonyms":[],"example":"I trained with weights all winter."},{"definition":"To proceed in sequence.","synonyms":[],"antonyms":[]},{"definition":"To move (a gun) laterally so that it points in a different direction.","synonyms":[],"antonyms":[],"example":"The assassin had trained his gun on the minister."},{"definition":"To encourage (a plant or branch) to grow in a particular direction or shape, usually by pruning and bending.","synonyms":[],"antonyms":[],"example":"The vine had been trained over the pergola."},{"definition":"To trace (a lode or any mineral appearance) to its head.","synonyms":[],"antonyms":[]},{"definition":"To create a trainer for; to apply cheats to (a game).","synonyms":[],"antonyms":[]},{"definition":"To draw along; to trail; to drag.","synonyms":[],"antonyms":[]},{"definition":"To draw by persuasion, artifice, or the like; to attract by stratagem; to entice; to allure.","synonyms":[],"antonyms":[]}],"synonyms":[],"antonyms":[]}],"license":{"name":"CC BY-SA 3.0","url":"https://creativecommons.org/licenses/by-sa/3.0"},"sourceUrls":["https://en.wiktionary.org/wiki/train"]},{"word":"train","phonetics":[],"meanings":[{"partOfSpeech":"noun","definitions":[{"definition":"Treachery; deceit.","synonyms":[],"antonyms":[]},{"definition":"A trick or stratagem.","synonyms":[],"antonyms":[]},{"definition":"A trap for animals; a snare.","synonyms":[],"antonyms":[]},{"definition":"A lure; a decoy.","synonyms":[],"antonyms":[]}],"synonyms":[],"antonyms":[]}],"license":{"name":"CC BY-SA 3.0",
#             "url":"https://creativecommons.org/licenses/by-sa/3.0"},"sourceUrls":["https://en.wiktionary.org/wiki/train"]}]