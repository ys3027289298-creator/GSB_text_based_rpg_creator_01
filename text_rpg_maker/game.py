import json


class ConfigError(Exception):
    """Raised when a scene configuration is invalid."""


class Game:
    def __init__(self, name, input_fn=input, output_fn=print):
        self.name = name
        self._input = input_fn
        self._output = output_fn
        self.config = None
        self._reset_state()

    def _reset_state(self):
        """Clear per-run state so replays never leak into each other."""
        self.current_scene = None
        self.history = []
        self.ending = None

    def cls(self):
        self._output("\n" * 50)

    def say(self, text) -> None:
        """ Basic print function. """
        self.cls()
        self._output(text)
        self._input("\n\n\nPress any key to continue.")

    def ask(self, question=str) -> str:
        """ Simple and plain question. Returns string. Accepts string """
        self.cls()
        return self._input(question)

    def ask_choices(self, question=str, choices=list) -> tuple:
        """ Ask questions with choices. Choices list should contain the choices you give to the player. Returns the choice index and text. """
        if not choices:
            raise ValueError("ask_choices() requires at least one choice")
        while True:
            self.cls()
            choices_string = "\n".join([f"{index + 1}) {choice}" for index, choice in enumerate(choices)])
            raw = self._input(f'{question}\n\n\n{choices_string}\n')
            try:
                answer = int(raw) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= answer < len(choices):
                return (answer, choices[answer])

    @staticmethod
    def load_config(path) -> dict:
        """ Load a scene configuration from a JSON file. """
        with open(path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
        Game.validate_config(config)
        return config

    @staticmethod
    def validate_config(config) -> None:
        """ Validate a scene configuration. Raises ConfigError on any problem. """
        if not isinstance(config, dict):
            raise ConfigError("Config must be a JSON object")
        scenes = config.get("scenes")
        if not scenes:
            raise ConfigError("Config has no scenes (empty config)")
        start = config.get("start")
        if not start:
            raise ConfigError("Config has no start scene")
        if start not in scenes:
            raise ConfigError(f"Start scene '{start}' is not defined")

        for scene_id, scene in scenes.items():
            if not isinstance(scene, dict):
                raise ConfigError(f"Scene '{scene_id}' must be an object")
            if "text" not in scene:
                raise ConfigError(f"Scene '{scene_id}' is missing its text")
            choices = scene.get("choices", [])
            if scene.get("ending"):
                continue
            if not choices:
                raise ConfigError(f"Scene '{scene_id}' has no choices and is not an ending")
            seen_texts = set()
            for choice in choices:
                choice_text = choice.get("text")
                if choice_text in seen_texts:
                    raise ConfigError(f"Scene '{scene_id}' has duplicate choice text: '{choice_text}'")
                seen_texts.add(choice_text)
                goto = choice.get("goto")
                if goto not in scenes:
                    raise ConfigError(f"Scene '{scene_id}' choice '{choice_text}' jumps to undefined scene '{goto}'")

        endings = [scene_id for scene_id, scene in scenes.items() if scene.get("ending")]
        if not endings:
            raise ConfigError("Config has no ending scene")

        # Every reachable scene must be able to reach an ending.
        reachable = {start}
        frontier = [start]
        while frontier:
            scene_id = frontier.pop()
            for choice in scenes[scene_id].get("choices", []):
                target = choice["goto"]
                if target not in reachable:
                    reachable.add(target)
                    frontier.append(target)
        for scene_id in sorted(reachable):
            if scenes[scene_id].get("ending"):
                continue
            visited = set()
            stack = [scene_id]
            reaches_ending = False
            while stack and not reaches_ending:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                if scenes[current].get("ending"):
                    reaches_ending = True
                else:
                    stack.extend(choice["goto"] for choice in scenes[current].get("choices", []))
            if not reaches_ending:
                raise ConfigError(f"Scene '{scene_id}' can never reach an ending")

    def load(self, config) -> None:
        """ Validate and attach a scene configuration to this game. """
        Game.validate_config(config)
        self.config = config
        self._reset_state()

    def play(self) -> str:
        """ Run the configured scene graph. Returns the ending scene id. """
        if self.config is None:
            raise ConfigError("No config loaded; call load() or load_config() first")
        self._reset_state()
        scenes = self.config["scenes"]
        scene_id = self.config["start"]
        while True:
            scene = scenes[scene_id]
            self.current_scene = scene_id
            self.history.append(scene_id)
            if scene.get("ending"):
                self.ending = scene_id
                self.say(scene["text"])
                return scene_id
            index, _ = self.ask_choices(scene["text"], [choice["text"] for choice in scene["choices"]])
            scene_id = scene["choices"][index]["goto"]
