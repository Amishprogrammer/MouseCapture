import json
import os

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(MODULE_DIR, "final file.json")

with open(DATA_FILE, "r", encoding="utf-8") as file:
    CODE_WORDS = json.load(file)