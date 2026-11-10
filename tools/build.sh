#!/bin/sh
# Draws every picture, makes every sound and writes scene.json and logic.json, all from this folder's code.
# Needs Python 3 with Pillow and NumPy. Run it from anywhere; it writes into the project folder above it.
set -e
here=$(cd "$(dirname "$0")" && pwd); root=$(dirname "$here"); cd "$here"
python3 -c "import art4; art4.build('$root')"
python3 art6_people.py "$root/assets"
python3 -c "import art6_creatures; art6_creatures.build('$root/assets')"
python3 -c "import art6_world; art6_world.build('$root/assets')"
python3 art6_ui.py "$root" "$root/assets"
python3 sound6.py "$root"
python3 make_game6.py "$root"
rm -f "$root/assets/contact.png"
echo "Done. Open the project in AnyDevKit Studio and build it."
