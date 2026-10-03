import json

from .game import Game

# Editor prompts and the config format keys are the stable public interface;
# do not change them.
PROMPTS = {
    "title": "Game title: ",
    "start": "Start scene id: ",
    "scene_id": "Scene id (leave empty to finish): ",
    "scene_text": "Scene text: ",
    "ending": "Is this an ending scene? (y/n): ",
    "choice_text": "Choice text (leave empty to finish choices): ",
    "choice_goto": "Choice jumps to scene: ",
    "save_path": "Save config to: ",
}


class Creator:
    """ Builds a scene configuration interactively or programmatically. """

    def __init__(self, input_fn=input, output_fn=print):
        self._input = input_fn
        self._output = output_fn
        self.config = {"title": "", "start": None, "scenes": {}}

    def set_title(self, title) -> "Creator":
        self.config["title"] = title
        return self

    def set_start(self, scene_id) -> "Creator":
        self.config["start"] = scene_id
        return self

    def add_scene(self, scene_id, text, ending=False, choices=None) -> "Creator":
        if scene_id in self.config["scenes"]:
            raise ValueError(f"Scene '{scene_id}' already exists")
        self.config["scenes"][scene_id] = {
            "text": text,
            "ending": bool(ending),
            "choices": list(choices) if choices else [],
        }
        if self.config["start"] is None:
            self.config["start"] = scene_id
        return self

    def add_choice(self, scene_id, text, goto) -> "Creator":
        self.config["scenes"][scene_id]["choices"].append({"text": text, "goto": goto})
        return self

    def mark_ending(self, scene_id) -> "Creator":
        self.config["scenes"][scene_id]["ending"] = True
        return self

    def validate(self) -> None:
        Game.validate_config(self.config)

    def save(self, path) -> None:
        self.validate()
        with open(path, "w", encoding="utf-8") as config_file:
            json.dump(self.config, config_file, ensure_ascii=False, indent=2)

    def run(self) -> dict:
        """ Interactive editor loop. Returns the finished config. """
        self.config["title"] = self._input(PROMPTS["title"])
        first_scene = self._input(PROMPTS["start"])
        if first_scene:
            self.config["start"] = first_scene
        while True:
            scene_id = self._input(PROMPTS["scene_id"])
            if not scene_id:
                break
            text = self._input(PROMPTS["scene_text"])
            is_ending = self._input(PROMPTS["ending"]).strip().lower().startswith("y")
            self.add_scene(scene_id, text, ending=is_ending)
            if self.config["start"] is None:
                self.config["start"] = scene_id
            while not is_ending:
                choice_text = self._input(PROMPTS["choice_text"])
                if not choice_text:
                    break
                goto = self._input(PROMPTS["choice_goto"])
                self.add_choice(scene_id, choice_text, goto)
        self.validate()
        save_path = self._input(PROMPTS["save_path"])
        if save_path:
            self.save(save_path)
        return self.config
