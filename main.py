# Standard Library
import os
import sys
import json
import time
import platform
import threading
import re
import webbrowser
from concurrent.futures import ThreadPoolExecutor

# Third-Party Libraries
import pytesseract
import pyperclip
import cv2
import numpy as np
import requests
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

from codelibrary import CODE_WORDS

# ── Platform detection ────────────────────────────────────────────────────────
PLATFORM = platform.system()  # 'Windows', 'Darwin', 'Linux'


def _find_tesseract():
    if PLATFORM == 'Windows':
        return r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    for path in [
        '/opt/homebrew/bin/tesseract',   # macOS Apple Silicon (Homebrew)
        '/usr/local/bin/tesseract',       # macOS Intel (Homebrew)
        '/usr/bin/tesseract',             # Linux
    ]:
        if os.path.exists(path):
            return path
    return 'tesseract'  # assume it's on PATH


pytesseract.pytesseract.tesseract_cmd = _find_tesseract()

# ── Screen capture (mss is ~10x faster than PIL.ImageGrab) ───────────────────
try:
    import mss as _mss_module
    _sct = _mss_module.mss()

    def grab_region(left: int, top: int, width: int, height: int) -> Image.Image:
        mon = {"left": left, "top": top, "width": width, "height": height}
        raw = _sct.grab(mon)
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

except ImportError:
    from PIL import ImageGrab

    def grab_region(left: int, top: int, width: int, height: int) -> Image.Image:
        return ImageGrab.grab(
            bbox=(left, top, left + width, top + height),
            all_screens=True,   # required on macOS for multi-monitor
        )

# ── Mouse position (pynput, no root on Mac) ───────────────────────────────────
_mouse_ctrl = pynput_mouse.Controller()


def get_mouse_position():
    pos = _mouse_ctrl.position
    return int(pos[0]), int(pos[1])


# ── App state ─────────────────────────────────────────────────────────────────
TARGET_WORDS_FILE = "target_words.json"
BOX_WIDTH_EM = 10
BOX_HEIGHT_EM = 4

_executor = ThreadPoolExecutor(max_workers=2)
_last_trigger: dict = {}
_DEBOUNCE_S = 0.5
_hotkey_listener = None


def _debounce(key: str) -> bool:
    now = time.monotonic()
    if now - _last_trigger.get(key, 0) < _DEBOUNCE_S:
        return False
    _last_trigger[key] = now
    return True


# ── Target words persistence ──────────────────────────────────────────────────
def load_target_words() -> dict:
    try:
        with open(TARGET_WORDS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "Name": "Name",
            "First Name": "First Name",
            "Last Name": "Last Name",
            "Full Name": "Name",
            "Email": "email@email.com",
            "Email Address": "email@email.com",
            "E-mail": "email.email.com",
            "Phone Number": "0000000000",
            "Mobile Number": "0000000000",
            "Contact Number": "0000000000",
        }


def save_target_words():
    with open(TARGET_WORDS_FILE, "w") as f:
        json.dump(TARGET_WORDS, f, indent=4)


# ── Edit target words UI ──────────────────────────────────────────────────────
def edit_target_words(root):
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
            key = selected_item.split(":")[0].strip()
            new_value = simpledialog.askstring(
                "Edit Value", f"Enter the new value for '{key}':", initialvalue=TARGET_WORDS[key]
            )
            if new_value is not None:
                TARGET_WORDS[key] = new_value
                update_listbox()

    def update_listbox():
        listbox.delete(0, tk.END)
        for key, value in TARGET_WORDS.items():
            listbox.insert(tk.END, f"{key}: {value}")

    def save_and_close():
        save_target_words()
        edit_window.destroy()

    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Target Words")
    listbox = tk.Listbox(edit_window, width=50)
    listbox.pack(padx=10, pady=10)
    update_listbox()
    ttk.Button(edit_window, text="Add", command=add_word).pack(pady=5)
    ttk.Button(edit_window, text="Delete", command=delete_word).pack(pady=5)
    ttk.Button(edit_window, text="Edit", command=edit_word).pack(pady=5)
    ttk.Button(edit_window, text="Save and Close", command=save_and_close).pack(pady=5)
    edit_window.protocol("WM_DELETE_WINDOW", save_and_close)


# ── Actions ───────────────────────────────────────────────────────────────────
def get_word_definition(word: str) -> str:
    word = word.split()[0]
    try:
        response = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                definitions = data[0]['meanings'][0]['definitions']
                return " ".join(d['definition'] for d in definitions)
        return "No definition found"
    except Exception:
        return "Error fetching definition"


def google_search(query: str, image_search: bool = False):
    if not query.strip():
        return
    if image_search:
        url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}"
    else:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)


def translate_text(query: str):
    if query:
        webbrowser.open(
            f"https://translate.google.com/?sl=auto&tl=en&text={query}&op=translate"
        )


FILE_PATH = os.path.join(os.getcwd(), "screenshot.jpg")
BING_IMAGE_SEARCH_URL = "https://www.bing.com/visualsearch"


def upload_to_google_lens():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )
    try:
        driver.get(BING_IMAGE_SEARCH_URL)
        upload_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )
        driver.execute_script("arguments[0].style.display = 'block';", upload_button)
        upload_button.send_keys(FILE_PATH)
        print("Image uploaded to Bing successfully!")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "visualSearchResults"))
        )
        print("Image processed. Browser left open — close it manually when done.")
        # Non-blocking: return, browser stays open via detach=True
    except Exception as e:
        print(f"Error during upload: {e}")


# ── Core capture + OCR ────────────────────────────────────────────────────────
def capture_box() -> Image.Image:
    x, y = get_mouse_position()
    box_width = BOX_WIDTH_EM * 16
    box_height = BOX_HEIGHT_EM * 16
    left = max(x - box_width // 2, 0)
    top = max(y - box_height // 2, 0)
    return grab_region(left, top, box_width, box_height)


def process_image(image: Image.Image) -> dict:
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    open_cv_image = cv2.resize(open_cv_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    open_cv_image = cv2.GaussianBlur(open_cv_image, (5, 5), 0)
    try:
        return pytesseract.image_to_data(open_cv_image, output_type=pytesseract.Output.DICT)
    except Exception as e:
        print(f"OCR error: {e}")
        return {'text': [], 'left': [], 'top': [], 'width': [], 'height': []}


def find_nearest_text(data: dict) -> str:
    return " ".join(w for w in data['text'] if w.strip())


def _capture_and_ocr() -> str:
    return find_nearest_text(process_image(capture_box()))


# ── Hotkey handlers (run in executor — non-blocking) ─────────────────────────
def _on_activate_a():
    if not _debounce('a'):
        return
    text = _capture_and_ocr()
    if not text:
        print("No text detected.")
        return
    print(f"OCR text: {text}")
    for key, value in TARGET_WORDS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.IGNORECASE):
            pyperclip.copy(value)
            print(f"Copied value for '{key}'.")
            break


def _on_activate_c():
    if not _debounce('c'):
        return
    text = _capture_and_ocr()
    if not text:
        return
    for key, value in CODE_WORDS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.IGNORECASE):
            pyperclip.copy(value)
            print(f"Copied code for '{key}'.")
            break


def _on_activate_g():
    if not _debounce('g'):
        return
    google_search(_capture_and_ocr())


def _on_activate_m():
    if not _debounce('m'):
        return
    text = _capture_and_ocr()
    pyperclip.copy(get_word_definition(text))
    print("Definition copied.")


def _on_activate_t():
    if not _debounce('t'):
        return
    translate_text(_capture_and_ocr())


def _on_activate_q():
    if not _debounce('q'):
        return
    img = capture_box()
    img.save(FILE_PATH, "JPEG")
    upload_to_google_lens()


def _dispatch(fn):
    _executor.submit(fn)


def _setup_hotkeys():
    global _hotkey_listener
    mapping = {
        '<ctrl>+<shift>+a': lambda: _dispatch(_on_activate_a),
        '<ctrl>+<shift>+c': lambda: _dispatch(_on_activate_c),
        '<ctrl>+<shift>+g': lambda: _dispatch(_on_activate_g),
        '<ctrl>+<shift>+m': lambda: _dispatch(_on_activate_m),
        '<ctrl>+<shift>+t': lambda: _dispatch(_on_activate_t),
        '<ctrl>+<shift>+q': lambda: _dispatch(_on_activate_q),
    }
    _hotkey_listener = pynput_keyboard.GlobalHotKeys(mapping)
    _hotkey_listener.start()
    print(
        "Hotkeys active:\n"
        "  Ctrl+Shift+A  = Fetch from target words\n"
        "  Ctrl+Shift+C  = Fetch code\n"
        "  Ctrl+Shift+G  = Google search\n"
        "  Ctrl+Shift+M  = Dictionary lookup\n"
        "  Ctrl+Shift+T  = Translate\n"
        "  Ctrl+Shift+Q  = Image search\n"
        "  Close window  = Exit"
    )


# ── Transparent overlay window ────────────────────────────────────────────────
def _configure_transparency(root, canvas):
    if PLATFORM == 'Windows':
        root.attributes("-transparentcolor", root['bg'])
    elif PLATFORM == 'Darwin':
        try:
            # On macOS, -transparent makes the window background truly transparent
            # while canvas-drawn items remain fully visible.
            root.wm_attributes("-transparent", True)
            root.configure(bg='black')
            canvas.configure(bg='black')
        except tk.TclError:
            root.attributes("-alpha", 0.01)
    else:
        root.attributes("-alpha", 0.01)


def create_transparent_box(root, canvas, clipboard_label):
    def update_box():
        try:
            x, y = get_mouse_position()
            half_w = BOX_WIDTH_EM * 16 // 2
            half_h = BOX_HEIGHT_EM * 16 // 2
            canvas.coords("capture_box", x - half_w, y - half_h, x + half_w, y + half_h)
            canvas.coords("clipboard_label", x, y + half_h + 35)

            clipboard_text = pyperclip.paste()
            truncated = clipboard_text[:30] + ("..." if len(clipboard_text) > 30 else "")
            clipboard_label.config(text=truncated, fg="green")

            root.after(100, update_box)
        except Exception as e:
            print(f"Overlay update error: {e}")

    canvas.create_rectangle(0, 0, 1, 1, outline="green", width=2, tags="capture_box")
    canvas.create_window(0, 0, window=clipboard_label, tags="clipboard_label")
    update_box()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global TARGET_WORDS, BOX_WIDTH_EM, BOX_HEIGHT_EM

    TARGET_WORDS = load_target_words()

    def update_box_width(value):
        global BOX_WIDTH_EM
        BOX_WIDTH_EM = int(round(float(value)))
        width_label.config(text=f"Width: {BOX_WIDTH_EM} em")

    def update_box_height(value):
        global BOX_HEIGHT_EM
        BOX_HEIGHT_EM = int(round(float(value)))
        height_label.config(text=f"Height: {BOX_HEIGHT_EM} em")

    def on_close():
        save_target_words()
        if _hotkey_listener:
            _hotkey_listener.stop()
        _executor.shutdown(wait=False)
        root.destroy()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{sw}x{sh}+0+0")

    canvas = tk.Canvas(root, width=sw, height=sh, highlightthickness=0)
    canvas.pack()

    _configure_transparency(root, canvas)

    clipboard_label = tk.Label(root, text=pyperclip.paste()[:30], fg="black")
    create_transparent_box(root, canvas, clipboard_label)

    width_label = tk.Label(root, text=f"Width: {BOX_WIDTH_EM} em", fg="black")
    height_label = tk.Label(root, text=f"Height: {BOX_HEIGHT_EM} em", fg="black")
    width_label.place(x=sw - 250, y=78)
    height_label.place(x=sw - 250, y=228)

    slider_width = ttk.Scale(
        root, from_=1, to=root.winfo_screenmmwidth() // 2,
        orient=tk.VERTICAL, command=update_box_width,
    )
    slider_width.set(BOX_WIDTH_EM)
    slider_width.place(x=sw - 200, y=100)

    slider_height = ttk.Scale(
        root, from_=1, to=root.winfo_screenmmheight() // 2,
        orient=tk.VERTICAL, command=update_box_height,
    )
    slider_height.set(BOX_HEIGHT_EM)
    slider_height.place(x=sw - 200, y=250)

    guide_text = (
        "Ctrl+Shift+O = Close\n"
        "Ctrl+Shift+A = Target words\n"
        "Ctrl+Shift+C = Fetch code\n"
        "Ctrl+Shift+G = Google search\n"
        "Ctrl+Shift+M = Dictionary\n"
        "Ctrl+Shift+T = Translate\n"
        "Ctrl+Shift+Q = Image search"
    )
    ttk.Label(root, text=guide_text, font=("Arial", 7), foreground="green").place(
        x=sw - 250, y=400
    )

    ttk.Button(root, text="Edit Target Words", command=lambda: edit_target_words(root)).place(
        x=sw - 250, y=350
    )

    _setup_hotkeys()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
