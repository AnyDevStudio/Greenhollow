# Greenhollow

A small 2.5D RPG for PS5 homebrew with ink-drawn art, made with
[AnyDevKit Studio](https://github.com/AnyDevStudio/AnyDevKit-Studio) from drag and drop scenes and jigsaw
logic blocks. It is an example from [AnyDevStudio](https://github.com/AnyDevStudio), built on
[AnyDevKit](https://github.com/boykopovar/AnyDevKit) by boykopovar.

![The village at dusk, with two cottages, Mira's fenced garden and the road east](docs/screens/village.jpg)

Talk to Mira in the village and take her quest. Go through the east gate into the woods, cut down slimes,
pick up the jelly they drop and bring three back to her for gold, a potion and enough XP to level up.

| | |
|---|---|
| ![Mira explains the slime problem in a dialog box](docs/screens/mira.jpg) | ![The hero swings a sword at a slime in the dark woods](docs/screens/woods.jpg) |
| Mira has a job for you | Slimes in the east woods |
| ![LEVEL UP in gold letters above the hero in the forest](docs/screens/level-up.jpg) | ![Inside the house, with a bed, a fireplace, a laid table and Tobin](docs/screens/house.jpg) |
| Every slime is worth XP | Tobin's bed fixes nearly everything |

- Three scenes: the village, a house you can walk into, and the forest
- A tilted camera: the ground leans away from you, and people, trees and houses stand up and pass in front of
  and behind each other
- Dialogue with a yes or no choice, and a quest tracker
- A bag with item counts and a potion you can drink
- Slimes that wander, chase you, hurt you, die, drop loot and come back
- Levels that raise your health and attack, a bed that heals you, and waking up in the village if you fall

The whole game is one `scene.json` and one `logic.json`, 1,231 blocks in all, with no hand-written game code.
Open it in Studio to see how each part is done.

## Controls

| Action | Controller | Keyboard in AnyPS5 |
|---|---|---|
| Walk | Left stick or D-pad | WASD or arrow keys |
| Talk, next, accept, sleep | Cross | Space or Enter |
| Sword | Square | Left mouse button |
| Bag | Triangle | I |
| Drink a potion, say no | Circle | C |

## Where it has run

It has run in the AnyPS5 compatibility layer on an Apple Silicon Mac at about 120 FPS, through a playthrough of
about a minute with no crash or GPU error. The pictures on this page are frames captured from that run. It has
not been run on a real PS5, and its sound has not been confirmed there.

The game logic was also played from start to finish by a scripted bot against the real game runtime on the
host, under address and undefined behavior sanitizers. `tools/gen_bot.py` writes that bot.

## Build

The tilted camera is newer than the latest Studio release, 0.1.0-alpha.3, which would lose it when saving. Until
a newer release is out, build [AnyDevKit Studio](https://github.com/AnyDevStudio/AnyDevKit-Studio) from `main`
and set up its PS5 tools. `CMakePresets.json` holds paths on your machine, so make it with `adk init` first:

```sh
adk init Greenhollow --deps <your .adk folder> --directory preset-source
cp preset-source/CMakePresets.json .
```

Then open this folder in Studio and press Build PS5 package. The prepared game folder is `build/package/app0`
and the single file package is `dist/ps5/Greenhollow.ffpfsc`.

## Art and sound

Every picture and sound is original and made by code, with no outside assets. `tools/art4.py` draws the current
art in ink lines and flat coats of paint, and its older neighbors `art.py`, `art2.py` and `art3.py` supply its
helpers and the sound effects and music. `tools/make_game.py` writes the scenes and blocks. To remake everything
from the `tools` folder, with Python 3, Pillow and NumPy:

```sh
python3 art.py ..
python3 -c "import art4; art4.build('..')"
python3 make_game.py ..
```

## License

GPL-2.0-only, the license of the AnyDevKit template and runtime this game is built on. See [LICENSE](LICENSE)
and [LICENSES](LICENSES).
