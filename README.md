# Text-Based-RPG-Creator
a text based rpg game creator for text based rpg fans.

## Usage

```python
from text_rpg_maker import *

game = Game('test')
ree = game.ask_choices("How are you?", ["Good!", "Meh...", "FeelsBadMan"])
game.say(ree)
```

## Scene configs

`Creator` builds a JSON scene config; `Game` parses and plays it.

```python
from text_rpg_maker import Creator, Game

creator = Creator()
(creator.set_title("Adventure")
        .add_scene("start", "You wake up at a crossroads.")
        .add_choice("start", "Enter the forest", "forest")
        .add_scene("forest", "You find a way home.", ending=True)
        .set_start("start"))
creator.save("game.json")          # validates before writing

game = Game("player")
game.load(Game.load_config("game.json"))
game.play()                        # returns the ending scene id
```

Config format (stable, do not change):

```json
{
  "title": "Adventure",
  "start": "start",
  "scenes": {
    "start": {
      "text": "You wake up at a crossroads.",
      "ending": false,
      "choices": [{"text": "Enter the forest", "goto": "forest"}]
    },
    "forest": {"text": "You find a way home.", "ending": true, "choices": []}
  }
}
```

`Game.validate_config` rejects empty configs, undefined `goto` targets,
duplicate choice text within a scene, and configs where an ending is
missing or unreachable. Run the tests with `python3 test.py`.
