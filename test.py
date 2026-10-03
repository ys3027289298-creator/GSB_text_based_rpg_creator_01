import json
import os
import tempfile
import unittest

from text_rpg_maker import Creator, Game
from text_rpg_maker.game import ConfigError


def scripted_input(answers):
    """Return an input_fn that replays the given answers, '' afterwards."""
    answers = iter(answers)

    def _input(prompt=""):
        return next(answers, "")

    return _input


def make_output():
    """Return (output_fn, lines) capturing everything the game prints."""
    lines = []
    return lines.append, lines


def multi_ending_config():
    """start -> forest/cave -> two endings."""
    return {
        "title": "Adventure",
        "start": "start",
        "scenes": {
            "start": {
                "text": "You wake up at a crossroads.",
                "ending": False,
                "choices": [
                    {"text": "Enter the forest", "goto": "forest"},
                    {"text": "Enter the cave", "goto": "cave"},
                ],
            },
            "forest": {
                "text": "The forest is calm. You find a way home.",
                "ending": True,
                "choices": [],
            },
            "cave": {
                "text": "The cave is dark.",
                "ending": False,
                "choices": [
                    {"text": "Go deeper", "goto": "deep"},
                    {"text": "Turn back", "goto": "start"},
                ],
            },
            "deep": {
                "text": "A dragon guards a treasure. You retire rich.",
                "ending": True,
                "choices": [],
            },
        },
    }


def play_with(config, answers):
    """Play a config with scripted answers; return (ending, history, output)."""
    output_fn, lines = make_output()
    game = Game("test", input_fn=scripted_input(answers), output_fn=output_fn)
    game.load(config)
    ending = game.play()
    return ending, list(game.history), list(lines), game


class ReproducedBugsTest(unittest.TestCase):
    """Each test maps to a bug reproduced against the original code."""

    def test_empty_scene_choices_raise_clear_error(self):
        # Was: IndexError on empty choices.
        output_fn, _ = make_output()
        game = Game("test", input_fn=scripted_input(["1"]), output_fn=output_fn)
        with self.assertRaises(ValueError):
            game.ask_choices("Where to?", [])

    def test_empty_config_rejected(self):
        game = Game("test")
        with self.assertRaises(ConfigError):
            game.load({})
        with self.assertRaises(ConfigError):
            game.load({"title": "x", "start": "s", "scenes": {}})

    def test_undefined_goto_rejected(self):
        config = multi_ending_config()
        config["scenes"]["start"]["choices"][0]["goto"] = "nowhere"
        with self.assertRaisesRegex(ConfigError, "undefined scene"):
            Game.validate_config(config)

    def test_duplicate_choices_rejected_in_config(self):
        config = multi_ending_config()
        config["scenes"]["start"]["choices"].append({"text": "Enter the forest", "goto": "cave"})
        with self.assertRaisesRegex(ConfigError, "duplicate choice"):
            Game.validate_config(config)

    def test_duplicate_choices_numbered_correctly(self):
        # Was: choices.index() made both duplicates show/select as the first.
        prompts = []

        def recording_input(prompt=""):
            prompts.append(prompt)
            return "2"

        output_fn, _ = make_output()
        game = Game("test", input_fn=recording_input, output_fn=output_fn)
        index, text = game.ask_choices("Pick a door:", ["Left door", "Left door"])
        self.assertEqual((index, text), (1, "Left door"))
        self.assertTrue(any("2) Left door" in prompt for prompt in prompts))

    def test_missing_ending_rejected(self):
        config = multi_ending_config()
        for scene_id, scene in config["scenes"].items():
            scene["ending"] = False
            if not scene["choices"]:
                scene["choices"] = [{"text": "Wander", "goto": "start"}]
        with self.assertRaisesRegex(ConfigError, "no ending"):
            Game.validate_config(config)

    def test_unreachable_ending_rejected(self):
        config = multi_ending_config()
        # From 'cave' the only move loops back to itself: cave is reachable
        # from the start but can never reach an ending.
        config["scenes"]["cave"]["choices"] = [{"text": "Wander in circles", "goto": "cave"}]
        with self.assertRaisesRegex(ConfigError, "never reach an ending"):
            Game.validate_config(config)

    def test_invalid_choice_number_does_not_crash(self):
        # Was: ValueError on 'abc', IndexError on out-of-range, negative wrap.
        output_fn, _ = make_output()
        game = Game(
            "test",
            input_fn=scripted_input(["abc", "0", "3", "-1", "2"]),
            output_fn=output_fn,
        )
        index, text = game.ask_choices("Pick:", ["Left", "Right"])
        self.assertEqual((index, text), (1, "Right"))

    def test_no_state_residue_between_replays(self):
        config = multi_ending_config()
        output_fn, _ = make_output()
        game = Game("test", input_fn=scripted_input(["1"]), output_fn=output_fn)
        game.load(config)
        first_ending = game.play()
        self.assertEqual(game.history, ["start", "forest"])
        # Replay with a different path on the SAME game object.
        game._input = scripted_input(["2", "1"])
        second_ending = game.play()
        self.assertEqual(game.history, ["start", "cave", "deep"])
        self.assertNotEqual(first_ending, second_ending)
        self.assertEqual(game.ending, second_ending)


class CreatorFlowTest(unittest.TestCase):
    """Full flow: empty config -> scenes -> multiple endings -> save/load."""

    def test_creator_from_empty_config_to_multi_ending(self):
        creator = Creator()
        self.assertEqual(creator.config["scenes"], {})
        (
            creator.set_title("Adventure")
            .add_scene("start", "You wake up at a crossroads.")
            .add_choice("start", "Enter the forest", "forest")
            .add_choice("start", "Enter the cave", "cave")
            .add_scene("forest", "The forest is calm. You find a way home.", ending=True)
            .add_scene("cave", "The cave is dark.")
            .add_choice("cave", "Go deeper", "deep")
            .add_choice("cave", "Turn back", "start")
            .add_scene("deep", "A dragon guards a treasure. You retire rich.", ending=True)
        )
        creator.set_start("start")
        creator.validate()
        self.assertEqual(creator.config, multi_ending_config())

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "game.json")
            creator.save(path)
            with open(path, encoding="utf-8") as saved:
                self.assertEqual(json.load(saved), multi_ending_config())
            loaded = Game.load_config(path)
            self.assertEqual(loaded, multi_ending_config())

        # Every branch reaches its own ending.
        ending_forest, history_forest, _, _ = play_with(creator.config, ["1"])
        self.assertEqual((ending_forest, history_forest), ("forest", ["start", "forest"]))
        ending_deep, history_deep, _, _ = play_with(creator.config, ["2", "1"])
        self.assertEqual((ending_deep, history_deep), ("deep", ["start", "cave", "deep"]))
        # Loop back to start, then leave via the forest.
        ending_loop, history_loop, _, _ = play_with(creator.config, ["2", "2", "1"])
        self.assertEqual(
            (ending_loop, history_loop), ("forest", ["start", "cave", "start", "forest"])
        )

    def test_interactive_editor_builds_same_config(self):
        answers = [
            "Adventure",            # title
            "start",                # start scene id
            "start",                # scene id
            "You wake up at a crossroads.",
            "n",                    # not an ending
            "Enter the forest", "forest",
            "Enter the cave", "cave",
            "",                     # finish choices
            "forest",
            "The forest is calm. You find a way home.",
            "y",                    # ending
            "cave",
            "The cave is dark.",
            "n",
            "Go deeper", "deep",
            "Turn back", "start",
            "",
            "deep",
            "A dragon guards a treasure. You retire rich.",
            "y",
            "",                     # finish scenes
            "",                     # don't save
        ]
        creator = Creator(input_fn=scripted_input(answers), output_fn=lambda *_: None)
        config = creator.run()
        self.assertEqual(config, multi_ending_config())


class DeterminismTest(unittest.TestCase):
    def test_same_config_same_inputs_same_output(self):
        config = multi_ending_config()
        runs = [play_with(config, ["2", "1"]) for _ in range(3)]
        endings, histories, outputs = zip(*[(r[0], tuple(r[1]), tuple(r[2])) for r in runs])
        self.assertEqual(len(set(endings)), 1)
        self.assertEqual(len(set(histories)), 1)
        self.assertEqual(len(set(outputs)), 1)

    def test_fresh_games_hold_no_residue(self):
        config = multi_ending_config()
        _, _, _, game_a = play_with(config, ["1"])
        _, _, _, game_b = play_with(config, ["1"])
        self.assertEqual(game_a.history, game_b.history)
        self.assertEqual(game_a.ending, game_b.ending)


if __name__ == "__main__":
    unittest.main(verbosity=2)
