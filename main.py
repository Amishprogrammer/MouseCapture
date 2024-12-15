import pytesseract
import pyautogui
import pyperclip
import cv2
import numpy as np
from PIL import ImageGrab
import tkinter as tk
import keyboard
import threading
from scipy.spatial import distance
import webbrowser


# Set up pytesseract path (update this based on your installation)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Dictionary of target words and their corresponding predefined terms
TARGET_WORDS = {
    # Personal Information
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

def google_search(query):
    """Search the extracted text on Google."""
    if query.strip():
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        print(f"Searching Google for: {query}")
    else:
        print("No valid text to search.")

def create_transparent_box(root, canvas, width, height, clipboard_label):
    """Create a transparent box with a green border around the mouse pointer and update clipboard text."""
    def update_box():
        try:
            # Get mouse position
            x, y = pyautogui.position()

            # Update the position of the rectangle
            canvas.coords(
                "capture_box",
                x - width // 2,
                y - height // 2,
                x + width // 2,
                y + height // 2
            )

            # Update the clipboard label position
            canvas.coords(
                "clipboard_label",
                x, y + height // 2 + 10  # Position below the box
            )

            # Update the clipboard content (truncate if too long)
            clipboard_text = pyperclip.paste()
            truncated_text = clipboard_text[:30] + ("..." if len(clipboard_text) > 30 else "")
            clipboard_label.config(text=f"{truncated_text}")

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
    """Capture a box of 10em x 4em around the mouse pointer and return the image."""
    x, y = pyautogui.position()
    box_width = 10 * 16  # 10em in pixels
    box_height = 4 * 16  # 4em in pixels
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
    data = pytesseract.image_to_data(open_cv_image, output_type=pytesseract.Output.DICT)
    return data

def find_nearest_text(data, mouse_x, mouse_y, box_left, box_top):
    """Find the sequence of words closest to the mouse pointer."""
    words = data['text']
    positions = zip(data['left'], data['top'], data['width'], data['height'])
    word_positions = []

    for word, (x, y, w, h) in zip(words, positions):
        if word.strip():
            word_center = ((x + w / 2) + box_left, (y + h / 2) + box_top)
            word_positions.append((word, word_center))

    word_positions.sort(key=lambda item: distance.euclidean((mouse_x, mouse_y), item[1]))
    nearest_text = " ".join([word for word, _ in word_positions[::-1]])
    return nearest_text

def start_application():
    """Start the main application loop."""
    print("Press 'Ctrl + Shift + A' to activate the box. Press 'Esc' to exit.")

    while True:
        try:
            if keyboard.is_pressed('ctrl+shift+a'):
                print("Box activated! Capturing...")
                mouse_x, mouse_y = pyautogui.position()
                screenshot = capture_box()
                box_left, box_top = mouse_x - (10 * 16) // 2, mouse_y - (4 * 16) // 2
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)

                if nearest_text:
                    print(f"Nearest Text: {nearest_text}")
                    for key, value in TARGET_WORDS.items():
                        if key.lower() in nearest_text.lower():
                            print(f"Target word '{key}' found! Copying corresponding value to clipboard.")
                            pyperclip.copy(value)
                            print("Copied to clipboard.")
                            break
                    else:
                        print("No target words found near the pointer. Searching on Google...")
                        google_search(nearest_text)
                else:
                    print("No text detected in the box.")

                # keyboard.wait('ctrl+shift+a')

            if keyboard.is_pressed('ctrl+shift+g'):
                print("Box activated! Capturing...")
                mouse_x, mouse_y = pyautogui.position()
                screenshot = capture_box()
                box_left, box_top = mouse_x - (10 * 16) // 2, mouse_y - (4 * 16) // 2
                data = process_image(screenshot)
                nearest_text = find_nearest_text(data, mouse_x, mouse_y, box_left, box_top)

                if nearest_text:
                    print("Searching on Google...")
                    google_search(nearest_text)
                else:
                    print("No text detected in the box.")

                # keyboard.wait('ctrl+shift+g')


            if keyboard.is_pressed('esc'):
                print("Exiting application.")
                break
        except Exception as e:
            print(f"Error: {e}")

def main():
    box_width = 10 * 16  # 10em in pixels
    box_height = 4 * 16  # 4em in pixels

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")

    canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="white")
    canvas.pack()

    clipboard_label = tk.Label(root, text=f"{pyperclip.paste()[:30]}...", bg="white", fg="black")
    create_transparent_box(root, canvas, box_width, box_height, clipboard_label)

    app_thread = threading.Thread(target=start_application, daemon=True)
    app_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()
