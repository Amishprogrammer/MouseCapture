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
import re  # For regex matching

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

def google_search(query):
    """Search the extracted text on Google."""
    if query.strip():
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        print(f"Searching Google for: {query}")
    else:
        print("No valid text to search.")

def create_transparent_box(root, canvas, width_em, height_em, clipboard_label):
    """Create a transparent box with a green border around the mouse pointer and update clipboard text."""
    width = width_em * 16
    height = height_em * 16

    def update_box():
        try:
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
        0, 0, width, height,
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
    """Process the image and perform OCR to extract text with positional information."""
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    open_cv_image = cv2.resize(open_cv_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    open_cv_image = cv2.GaussianBlur(open_cv_image, (5, 5), 0)

    try:
        data = pytesseract.image_to_data(open_cv_image, output_type=pytesseract.Output.DICT)
        # print(data)
    except Exception as e:
        print(f"Error in OCR processing: {e}")
        data = {'text': [], 'left': [], 'top': [], 'width': [], 'height': []}

    return data

def find_nearest_text(data, mouse_x, mouse_y, box_left, box_top):
    """Find and arrange text from OCR output in a spatially consistent order."""
    words = data['text']
    lefts = data['left']
    tops = data['top']
    widths = data['width']
    heights = data['height']

    # valid_words = [
    #     {"text": word, "left": left, "top": top, "width": width, "height": height}
    #     for word, left, top, width, height in zip(words, lefts, tops, widths, heights)
    #     if word.strip()
    # ]

    # lines = []
    # line_threshold = 10

    # for word_data in valid_words:
    #     added_to_line = False
    #     for line in lines:
    #         if abs(line[0]['top'] - word_data['top']) < line_threshold:
    #             line.append(word_data)
    #             added_to_line = True
    #             break
    #     if not added_to_line:
    #         lines.append([word_data])

    # lines.sort(key=lambda line: min(word['top'] for word in line))

    # sorted_lines = []
    # for line in lines:
    #     line.sort(key=lambda word: word['left'])
    #     sorted_lines.append(" ".join(word['text'] for word in line))

    # arranged_text = "\n".join(sorted_lines)
    arranged_text = " ".join(words)
    return arranged_text

def start_application():
    """Start the main application loop."""
    print("Press 'Ctrl + Shift + A' to activate the box. Press 'Esc' to exit.")

    while True:
        try:
            if keyboard.is_pressed('ctrl+shift+a'):
                print("Box activated! Capturing...")
                mouse_x, mouse_y = pyautogui.position()
                screenshot = capture_box()
                box_left, box_top = mouse_x - (BOX_WIDTH_EM * 16) // 2, mouse_y - (BOX_HEIGHT_EM * 16) // 2
                data = process_image(screenshot)
                if data and 'text' in data:
                    nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)
                    print(f"Arranged Text:\n{nearest_text}")
                else:
                    nearest_text = ""

                if nearest_text:
                    print(f"Nearest Text: {nearest_text}")
                    for key, value in TARGET_WORDS.items():
                        # Match full phrases using regex
                        pattern = r'\b' + re.escape(key) + r'\b'
                        if re.search(pattern, nearest_text, re.IGNORECASE):
                            print(f"Target word '{key}' found! Copying corresponding value to clipboard.")
                            pyperclip.copy(value)
                            print("Copied to clipboard.")
                            break
                else:
                    print("No text detected in the box.")

            if keyboard.is_pressed('ctrl+shift+g'):
                print("Box activated! Capturing...")
                mouse_x, mouse_y = pyautogui.position()
                screenshot = capture_box()
                box_left, box_top = mouse_x - (BOX_WIDTH_EM * 16) // 2, mouse_y - (BOX_HEIGHT_EM * 16) // 2
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)
                print(f"Arranged Text:\n{nearest_text}")

                if nearest_text:
                    print("Searching on Google...")
                    google_search(nearest_text)
                else:
                    print("No text detected in the box.")

            if keyboard.is_pressed('esc'):
                print("Exiting application.")
                break
        except Exception as e:
            print(f"Error: {e}")

def main():
    def update_box_width(value):
        global BOX_WIDTH_EM
        BOX_WIDTH_EM = int(round(float(value)))

    def update_box_height(value):
        global BOX_HEIGHT_EM
        BOX_HEIGHT_EM = int(round(float(value)))

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")

    canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="white")
    canvas.pack()

    clipboard_label = tk.Label(root, text=f"{pyperclip.paste()[:30]}...", bg="white", fg="black")
    create_transparent_box(root, canvas, BOX_WIDTH_EM, BOX_HEIGHT_EM, clipboard_label)

    slider_width = ttk.Scale(root, from_=1, to=50, orient=tk.VERTICAL, command=update_box_width)
    slider_width.set(BOX_WIDTH_EM)
    slider_width.place(x=root.winfo_screenwidth() - 200, y=100)

    slider_height = ttk.Scale(root, from_=1, to=20, orient=tk.VERTICAL, command=update_box_height)
    slider_height.set(BOX_HEIGHT_EM)
    slider_height.place(x=root.winfo_screenwidth() - 200, y=200)

    label_width = ttk.Label(root, text="Width", background="white", foreground="black")
    label_width.place(x=root.winfo_screenwidth() - 200, y=80)

    label_height = ttk.Label(root, text="Height", background="white", foreground="black")
    label_height.place(x=root.winfo_screenwidth() - 200, y=180)

    app_thread = threading.Thread(target=start_application, daemon=True)
    app_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()
