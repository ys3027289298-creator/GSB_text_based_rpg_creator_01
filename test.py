import io
import unittest

from text_rpg_maker import Game, ConfigError

CONFIG = {
    "start": "wake",
    "scenes": {
        "wake": {
            "text": "You wake at a crossroads.",
            "choices": [
                {"text": "Go left", "goto": "forest"},
                {"text": "Go right", "goto": "castle"},
            ],
        },
        "forest": {
            "text": "A dark forest.",
            "choices": [
                {"text": "Fight the wolf", "goto": "bad_end"},
                {"text": "Run home", "goto": "neutral_end"},
            ],
        },
        "castle": {
            "text": "An abandoned castle.",
            "choices": [
                {"text": "Claim the throne", "goto": "good_end"},
                {"text": "Walk away", "goto": "neutral_end"},
            ],
        },
        "good_end": {"text": "You become ruler!", "ending": True},
        "neutral_end": {"text": "You live an ordinary life.", "ending": True},
        "bad_end": {"text": "The wolf wins.", "ending": True},
    },
}


class ScriptedIO:
    """ Feeds scripted answers; records everything shown. """

    def __init__(self, answers):
        self.answers = list(answers)
        self.output = io.StringIO()

    def input_fn(self, prompt=""):
        self.output.write(str(prompt))
        if str(prompt).rstrip().endswith("Press any key to continue."):
            return ""
        if not self.answers:
            raise AssertionError("Game asked for more input than scripted")
        return str(self.answers.pop(0))

    def output_fn(self, value=""):
        self.output.write(str(value) + "\n")


def make_game(config, answers):
    io_helper = ScriptedIO(answers)
    game = Game("test", config, input_fn=io_helper.input_fn,
                output_fn=io_helper.output_fn)
    return game, io_helper


class ConfigValidationTests(unittest.TestCase):
    def test_empty_config(self):
        with self.assertRaises(ConfigError):
            Game("test", {})
        with self.assertRaises(ConfigError):
            Game("test", {"start": "x", "scenes": {}})

    def test_missing_start(self):
        config = {"scenes": {"e": {"ending": True, "text": "e"}}}
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_undefined_start_scene(self):
        config = {"start": "nope", "scenes": {"e": {"ending": True}}}
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_undefined_jump(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "a", "choices": [{"text": "go", "goto": "ghost"}]},
                "end": {"text": "end", "ending": True},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_empty_scene_without_ending(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "dead end", "choices": []},
                "end": {"text": "end", "ending": True},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_duplicate_choices(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "a", "choices": [
                    {"text": "Same", "goto": "end"},
                    {"text": "Same", "goto": "end"},
                ]},
                "end": {"text": "end", "ending": True},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_missing_ending(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "a", "choices": [{"text": "loop", "goto": "b"}]},
                "b": {"text": "b", "choices": [{"text": "loop", "goto": "a"}]},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_ending_unreachable_from_start(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "a", "choices": [{"text": "loop", "goto": "a"}]},
                "end": {"text": "end", "ending": True},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)

    def test_choice_without_goto(self):
        config = {
            "start": "a",
            "scenes": {
                "a": {"text": "a", "choices": [{"text": "nowhere"}]},
                "end": {"text": "end", "ending": True},
            },
        }
        with self.assertRaises(ConfigError):
            Game("test", config)


class AskChoicesTests(unittest.TestCase):
    def setUp(self):
        self.game = Game("standalone", input_fn=None, output_fn=None)

    def test_invalid_then_valid_input(self):
        helper = ScriptedIO(["abc", "4", "0", "-1", "2"])
        game = Game("standalone", input_fn=helper.input_fn,
                    output_fn=helper.output_fn)
        index, text = game.ask_choices("Pick one", ["Alpha", "Beta"])
        self.assertEqual((index, text), (1, "Beta"))

    def test_whitespace_numeric_input(self):
        helper = ScriptedIO([" 2 "])
        game = Game("standalone", input_fn=helper.input_fn,
                    output_fn=helper.output_fn)
        index, text = game.ask_choices("Pick one", ["Alpha", "Beta"])
        self.assertEqual((index, text), (1, "Beta"))

    def test_duplicate_choice_labels_keep_position(self):
        helper = ScriptedIO(["2"])
        game = Game("standalone", input_fn=helper.input_fn,
                    output_fn=helper.output_fn)
        index, text = game.ask_choices("Pick one", ["Same", "Same", "Other"])
        self.assertEqual(index, 1)
        self.assertIn("1) Same", helper.output.getvalue())
        self.assertIn("2) Same", helper.output.getvalue())
        self.assertIn("3) Other", helper.output.getvalue())

    def test_empty_choices_raises(self):
        helper = ScriptedIO([])
        game = Game("standalone", input_fn=helper.input_fn,
                    output_fn=helper.output_fn)
        with self.assertRaises(ConfigError):
            game.ask_choices("Pick one", [])

    def test_prompts_unchanged(self):
        helper = ScriptedIO([""])
        game = Game("standalone", input_fn=helper.input_fn,
                    output_fn=helper.output_fn)
        game.say("Hello")
        self.assertIn("\n\n\nPress any key to continue.",
                      helper.output.getvalue())
        helper.answers.append("1")
        game.ask_choices("Q?", ["A"])
        self.assertIn("Q?\n\n\n1) A\n", helper.output.getvalue())


class PlaythroughTests(unittest.TestCase):
    def test_full_flow_empty_config_to_multiending(self):
        game = Game("test", input_fn=lambda p: "", output_fn=lambda v="": None)
        with self.assertRaises(ConfigError):
            Game("test", {})
        with self.assertRaises(ConfigError):
            game.play()
        game.load_config(CONFIG)
        self.assertEqual(sorted(self._endings(game)),
                         ["bad_end", "good_end", "neutral_end"])

    @staticmethod
    def _endings(game):
        return [sid for sid, scene in game.config["scenes"].items()
                if scene.get("ending")]

    def test_path_to_good_ending(self):
        game, helper = make_game(CONFIG, ["2", "1"])  # right -> throne
        ending = game.play()
        self.assertEqual(ending, "good_end")
        self.assertTrue(game.finished)
        self.assertEqual(game.visited, ["wake", "castle", "good_end"])

    def test_path_to_bad_ending(self):
        game, _ = make_game(CONFIG, ["1", "1"])  # left -> fight
        self.assertEqual(game.play(), "bad_end")

    def test_path_to_neutral_ending(self):
        game, _ = make_game(CONFIG, ["1", "2"])  # left -> run
        self.assertEqual(game.play(), "neutral_end")
        game, _ = make_game(CONFIG, ["2", "2"])  # right -> walk away
        self.assertEqual(game.play(), "neutral_end")

    def test_state_resets_on_replay(self):
        game, _ = make_game(CONFIG, ["1", "1", "2", "1"])
        first = game.play()
        self.assertEqual(first, "bad_end")
        self.assertEqual(game.current_scene, "bad_end")
        second = game.play()
        self.assertEqual(second, "good_end")
        self.assertEqual(game.current_scene, "good_end")
        self.assertEqual(game.visited, ["wake", "castle", "good_end"])
        self.assertEqual(game.ending, "good_end")

    def test_invalid_input_during_play_does_not_crash(self):
        game, _ = make_game(CONFIG, ["x", "9", "2", "1"])
        self.assertEqual(game.play(), "good_end")

    def test_same_config_same_inputs_deterministic(self):
        scripts = (["1", "1"], ["1", "2"], ["2", "1"], ["2", "2"],
                   ["x", "-3", "2", "2"], ["2", "0", "y", "1"])
        recorded = {}
        for answers in scripts:
            runs = []
            transcript_a = transcript_b = None
            for run in range(3):
                helper = ScriptedIO(answers)
                game = Game("test", CONFIG,
                            input_fn=helper.input_fn,
                            output_fn=helper.output_fn)
                runs.append((game.play(), tuple(game.visited)))
                if run == 0:
                    transcript_a = helper.output.getvalue()
                elif run == 2:
                    transcript_b = helper.output.getvalue()
            ending = {result[0] for result in runs}
            path = {result[1] for result in runs}
            self.assertEqual(len(ending), 1)
            self.assertEqual(len(path), 1)
            self.assertEqual(transcript_a, transcript_b)

    def test_each_ending_reachable_with_scripted_inputs(self):
        targets = {"bad_end": ["1", "1"], "neutral_end": ["1", "2"],
                   "good_end": ["2", "1"]}
        for expected, answers in targets.items():
            game, _ = make_game(CONFIG, answers)
            self.assertEqual(game.play(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
