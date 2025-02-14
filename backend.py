import yaml
import os
import math

DATA_DIR = "./Data"
TEXT_PRESETS_DIR = os.path.join(DATA_DIR, "Text Presets")
KEYBOARD_PRESETS_DIR = os.path.join(DATA_DIR, "Keyboard Presets")

### KEYBOARD HANDLING ###

class KeyboardLayout:
    def __init__(self, name, note, sub_boards):
        self.name = name
        self.note = note
        self.sub_boards = [SubBoard(**sub_board_data) for sub_board_data in sub_boards]

class SubBoard:
    def __init__(self, name, offset, rotation, keys):
        self.name = name
        self.offset = offset  # [x, y]
        self.rotation = rotation # 0-360
        self.keys = [Key(**key_data) for key_data in keys]

class Key:
    def __init__(self, offset, rotation, width, height, row, key_codes, finger, is_home_row):
        self.offset = offset  # [x, y]
        self.rotation = rotation # 0-360
        self.size = [width, height] # [x, y]
        self.row = row
        self.key_codes = key_codes  # Dictionary: {'base': 'a', 'shift': 'A'}
        self.finger = finger
        self.is_home_row = is_home_row

def load_keyboard_layout(filepath):
    with open(filepath, 'r') as file:
        keyboard_data = yaml.safe_load(file)
        return KeyboardLayout(**keyboard_data)

def list_keyboard_layouts():
    keyboard_files = [f for f in os.listdir(KEYBOARD_PRESETS_DIR) if f.endswith('.yaml') or f.endswith('.yml')]
    return [f.split('.')[0] for f in keyboard_files] # Return names without extension

def get_keyboard_layout_filepath(layout_name):
    yaml_filepath = os.path.join(KEYBOARD_PRESETS_DIR, f"{layout_name}.yaml")
    yml_filepath = os.path.join(KEYBOARD_PRESETS_DIR, f"{layout_name}.yml")

    if os.path.exists(yaml_filepath):
        return yaml_filepath
    elif os.path.exists(yml_filepath):
        return yml_filepath
    else:
        raise Exception("That file does not exist.")

def get_key_for_char(keyboard_layout, char):
    for sub_board in keyboard_layout.sub_boards:
        for key in sub_board.keys:
            for code_type, code_value in key.key_codes.items(): # Iterate through 'base', 'shift', etc.
                target_char = None
                if isinstance(code_value, str) and code_value.startswith("u:"):
                    try:
                        unicode_val = int(code_value[2:]) # Now correctly parses negative unicode too
                        target_char = chr(unicode_val) if unicode_val >= 0 else str(code_value) # Keep negative unicode as string
                    except ValueError:
                        print(f"Warning: Invalid unicode format: {code_value}")
                        continue # Skip if invalid unicode
                else:
                    target_char = code_value # Treat as literal character

                if target_char == char:
                    return key, code_type == 'shift' # Return key and if shift is needed
    return None, False # Character not found


### TEXT HANDLING ###


def load_text_preset(filepath):
    with open(filepath, 'r', encoding='utf-8') as file: # Handle different encodings
        return file.read()

def list_text_presets():
    text_files = [f for f in os.listdir(TEXT_PRESETS_DIR) if f.endswith('.txt')]
    return [f.split('.')[0] for f in text_files] # Return names without extension

def get_text_preset_filepath(preset_name):
    return os.path.join(TEXT_PRESETS_DIR, f"{preset_name}.txt")


### ANALYSIS ###

def text_to_key_sequence(keyboard_layout, text):
    key_sequence = []
    left_shift_key = None
    right_shift_key = None

    for sub_board in keyboard_layout.sub_boards:
        for key in sub_board.keys:
            for code_type, code_value in key.key_codes.items():
                if code_value == 'u:-1': # Identify Left Shift key by negative unicode
                    left_shift_key = key
                elif code_value == 'u:-2': # Identify Right Shift key by negative unicode
                    right_shift_key = key

    if left_shift_key is None:
        print("Warning: Left Shift key (u:-1) not found in layout. Shift functionality might be limited.")
    if right_shift_key is None:
        print("Warning: Right Shift key (u:-2) not found in layout.")


    for char in text:
        key, shift_needed = get_key_for_char(keyboard_layout, char)
        if key:
            if shift_needed:
                shift_to_use = left_shift_key # Default to left shift
                if left_shift_key and right_shift_key and left_shift_key.finger == key.finger:
                    shift_to_use = right_shift_key # Use right shift if character key and left shift are on same finger
                if shift_to_use:
                    key_sequence.append(shift_to_use)
                    key_sequence.append(key)
                else:
                    print("Warning: Shift needed but no shift key available or selectable for char:", char)
            else:
                key_sequence.append(key)
        else:
            print(f"Warning: Character '{char}' not found on keyboard layout, skipping: '{char}'")

    return key_sequence

def calculate_distance(key1, key2):
    if key1 is None or key2 is None:
        return 0.0
    x1, y1 = key1.offset
    x2, y2 = key2.offset
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def calculate_finger_distances(keyboard_layout, key_sequence):
    finger_distances = {}
    home_row_keys = {} # Dictionary to store home row key for each finger
    last_major_key = None

    # 1. Pre-process to find home row keys for each finger
    for sub_board in keyboard_layout.sub_boards:
        for key in sub_board.keys:
            if key.is_home_row and key.finger:
                if key.finger not in home_row_keys: # Take the first home row key found for each finger
                    home_row_keys[key.finger] = key
                    finger_distances[key.finger] = 0.0 # Initialize distance for each finger

    # 2. Iterate through the key sequence and calculate distances
    for current_key in key_sequence:
        if not current_key.finger: # Skip keys without finger assignment (e.g., modifiers if not assigned finger)
            continue
        print("cur:", current_key.key_codes)

        reference_key = None
        if last_major_key and last_major_key.finger == current_key.finger:
            reference_key = last_major_key
        else:
            reference_key = home_row_keys.get(current_key.finger) # Get home row key for current finger
        print("ref:", reference_key.key_codes)

        distance = calculate_distance(reference_key, current_key)

        finger_distances[current_key.finger] += distance

        is_modifier_key = False # Check if current_key is a modifier key (negative unicode)
        for code_value in current_key.key_codes.values():
            if isinstance(code_value, str) and code_value.startswith("u:-"):
                is_modifier_key = True
                break # No need to check further key codes if one is negative unicode

        if not is_modifier_key: # Update last_major_key only if it's NOT a modifier key
            last_major_key = current_key

    return finger_distances

def analyze_layout(keyboard_layout_name, text_preset_name):
    keyboard = load_keyboard_layout(get_keyboard_layout_filepath(keyboard_layout_name))
    text = load_text_preset(get_text_preset_filepath(text_preset_name))
    key_sequence = text_to_key_sequence(keyboard, text) # Generate key sequence

    finger_distance_results = calculate_finger_distances(keyboard, key_sequence) # Pass key sequence

    return {
        "keyboard_name": keyboard.name,
        "text_preset_name": text_preset_name,
        "average_key_distance": finger_distance_results, # Return finger distances directly
    }


if __name__ == "__main__": # Only runs when backend.py is executed directly
    layout_name = "QWERTY Layout"
    filepath = get_keyboard_layout_filepath(layout_name)
    keyboard = load_keyboard_layout(filepath)
    print(f"Loaded keyboard: {keyboard.name}")
    for sub_board in keyboard.sub_boards:
        print(f"  Sub-board: {sub_board.name}")
        for key in sub_board.keys:
            print(f"    Key: {key.key_codes}, Finger: {key.finger}, Home Row: {key.is_home_row}")

    print("\n--- Text Loading Test ---")
    text_preset_name = "English: Alice in Wonderland, Chapter 1"
    text_filepath = get_text_preset_filepath(text_preset_name)
    text_content = load_text_preset(text_filepath)
    lines = text_content.splitlines()
    if lines:
        first_line = lines[0]
        print(f"First line of '{text_preset_name}':")
        print(first_line)
    else:
        print(f"Text file '{text_preset_name}' is empty.")

    print("\n--- get_key_for_char Test ---")
    test_chars = ['a', 'A', '1', '!', '?', ' ', '\t']
    for char in test_chars:
        key, shift_needed = get_key_for_char(keyboard, char)
        if key:
            print(f"Character '{char}': Key found - {key.key_codes}, Finger: {key.finger}, Shift needed: {shift_needed}")
        else:
            print(f"Character '{char}': Key not found on layout.")

    print("\n--- text_to_key_sequence Test ---")
    test_text = "Hello World!\tTab?`~"
    key_sequence = text_to_key_sequence(keyboard, test_text)
    print(f"Key sequence for '{test_text}':")
    for key in key_sequence:
        print(f"Key: {key.key_codes}, Finger: {key.finger}")

    print("\n--- calculate_finger_distances Test (Short Text) ---")
    test_key_sequence_short = text_to_key_sequence(keyboard, "Test")
    finger_distances_short = calculate_finger_distances(keyboard, test_key_sequence_short)
    print("Finger Distances (Short Text 'Test'):")
    for finger, distance in finger_distances_short.items():
        print(f"  {finger}: {distance:.2f}")

    print("\n--- calculate_finger_distances Test (Larger Text Sample) ---")
    large_text_preset_name = "English: Alice in Wonderland, Chapter 1" # Use your larger text file name
    large_text = load_text_preset(get_text_preset_filepath(large_text_preset_name))
    large_key_sequence = text_to_key_sequence(keyboard, large_text)
    finger_distances_large = calculate_finger_distances(keyboard, large_key_sequence)
    print(f"Finger Distances (Larger Text Sample - '{large_text_preset_name}'):")
    for finger, distance in finger_distances_large.items():
        print(f"  {finger}: {distance:.2f}")