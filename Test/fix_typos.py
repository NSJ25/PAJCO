import re

# Read the file
with open('main_DEBUG_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the typos: =capteur.value -> =capteur.value (add space)
content = re.sub(r'=capteur\.value\(', '=capteur.value(', content)

# Fix result =detect_vehicle -> result = detect_vehicle
content = re.sub(r'result =detect_vehicle', 'result = detect_vehicle', content)

# Write back
with open('main_DEBUG_v2.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")