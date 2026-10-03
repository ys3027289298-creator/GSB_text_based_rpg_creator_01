class ConfigError(Exception):
    """ Raised when a game configuration (or a scene inside it) is invalid. """


class Game:
    def __init__(self, name, config=None, input_fn=input, output_fn=print):
        self.name = name
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.config = None
        self.current_scene = None
        self.visited = []
        self.finished = False
        self.ending = None
        if config is not None:
            self.load_config(config)

    def cls(self):
        print = self.output_fn
        print("\n" * 50)

    def say(self, text) -> None:
        """ Basic print function. """
        self.cls()
        self.output_fn(text)
        self.input_fn("\n\n\nPress any key to continue.")

    def ask(self, question=str) -> str:
        """ Simple and plain question. Returns string. Accepts string """
        self.cls()
        return self.input_fn(question)

    def ask_choices(self, question=str, choices=list) -> tuple:
        """ Ask questions with choices. Choices list should contain the choices you give to the player. Returns the choice index and text. """
        self.cls()
        if not choices:
            raise ConfigError("Cannot present choices: the scene has no options.")
        choices_string = "\n".join(
            [f"{index + 1}) {choice}" for index, choice in enumerate(choices)]
        )
        prompt = f'{question}\n\n\n{choices_string}\n'
        while True:
            raw = self.input_fn(prompt)
            try:
                answer = int(raw) - 1
            except (TypeError, ValueError):
                self.output_fn("Please enter the number of one of the choices above.")
                continue
            if 0 <= answer < len(choices):
                return (answer, choices[answer])
            self.output_fn(f"Please enter a number between 1 and {len(choices)}.")

    def load_config(self, config) -> None:
        """ Validate and load a scenario configuration created by the RPG creator. """
        self.validate_config(config)
        self.config = config
        self.current_scene = None
        self.visited = []
        self.finished = False
        self.ending = None

    @staticmethod
    def validate_config(config) -> None:
        if not isinstance(config, dict):
            raise ConfigError("Configuration must be a mapping/dict.")
        scenes = config.get("scenes")
        if not scenes or not isinstance(scenes, dict):
            raise ConfigError("Configuration defines no scenes.")

        start = config.get("start")
        if start is None:
            raise ConfigError("Configuration has no start scene.")
        if start not in scenes:
            raise ConfigError(f"Start scene {start!r} is not defined.")

        ending_ids = set()
        for scene_id, scene in scenes.items():
            if not isinstance(scene, dict):
                raise ConfigError(f"Scene {scene_id!r} must be a mapping/dict.")
            is_ending = bool(scene.get("ending"))
            if is_ending:
                ending_ids.add(scene_id)
                continue
            choices = scene.get("choices")
            if not choices:
                raise ConfigError(f"Scene {scene_id!r} has no choices and is not an ending.")
            choice_texts = [choice.get("text") for choice in choices]
            if len(set(choice_texts)) != len(choice_texts):
                raise ConfigError(f"Scene {scene_id!r} contains duplicate choices.")
            for choice in choices:
                target = choice.get("goto")
                if target is None:
                    raise ConfigError(
                        f"A choice in scene {scene_id!r} has no goto target."
                    )
                if target not in scenes:
                    raise ConfigError(
                        f"Scene {scene_id!r} jumps to undefined scene {target!r}."
                    )

        if not ending_ids:
            raise ConfigError("Configuration has no ending scene.")
        reachable = {start}
        frontier = [start]
        while frontier:
            scene_id = frontier.pop()
            if scene_id in ending_ids:
                continue
            for choice in scenes[scene_id].get("choices", []):
                target = choice["goto"]
                if target not in reachable:
                    reachable.add(target)
                    frontier.append(target)
        if not reachable & ending_ids:
            raise ConfigError("No ending is reachable from the start scene.")

    def play(self) -> str:
        """ Run one full playthrough. State is reset on every call. """
        if self.config is None:
            raise ConfigError("No configuration loaded.")
        self.current_scene = self.config["start"]
        self.visited = []
        self.finished = False
        self.ending = None

        scenes = self.config["scenes"]
        while True:
            self.visited.append(self.current_scene)
            scene = scenes[self.current_scene]
            text = scene.get("text", "")
            if scene.get("ending"):
                self.say(text)
                self.finished = True
                self.ending = self.current_scene
                return self.ending
            self.say(text)
            choices = [choice["text"] for choice in scene["choices"]]
            answer, _ = self.ask_choices(scene.get("question", text), choices)
            self.current_scene = scene["choices"][answer]["goto"]
