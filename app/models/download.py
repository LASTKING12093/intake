from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class State(StrEnum):
    READY = "Ready"
    INFO = "Getting info"
    WAITING = "Waiting"
    DOWNLOADING = "Downloading"
    PROCESSING = "Processing"
    CONVERTING = "Converting"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


ACTIVE = {State.INFO, State.DOWNLOADING, State.PROCESSING, State.CONVERTING}
TRANSITIONS = {
    State.READY: {State.WAITING, State.CANCELLED},
    State.WAITING: {State.INFO, State.DOWNLOADING, State.PAUSED, State.CANCELLED, State.FAILED},
    State.INFO: {State.DOWNLOADING, State.FAILED, State.CANCELLED, State.PAUSED},
    State.DOWNLOADING: {State.PROCESSING, State.CONVERTING, State.COMPLETED, State.FAILED, State.CANCELLED, State.PAUSED},
    State.PROCESSING: {State.CONVERTING, State.COMPLETED, State.FAILED, State.CANCELLED, State.PAUSED},
    State.CONVERTING: {State.PROCESSING, State.COMPLETED, State.FAILED, State.CANCELLED, State.PAUSED},
    State.PAUSED: {State.WAITING, State.CANCELLED},
    State.FAILED: {State.WAITING, State.CANCELLED},
    State.CANCELLED: {State.WAITING},
    State.COMPLETED: set(),
}


@dataclass
class Options:
    mode: str = "Video"
    container: str = "MP4"
    quality: str = "Best"
    metadata: bool = True
    thumbnail: bool = False
    subtitle: str = ""
    auto_subtitle: bool = False
    subtitle_mode: str = "Embed into video"
    video_codec: str = "Auto"
    audio_codec: str = "Auto"
    lyrics: bool = True
    filename: str = ""


@dataclass
class Job:
    url: str
    info: dict
    options: Options
    destination: str
    id: str = field(default_factory=lambda: uuid4().hex)
    state: State = State.READY
    progress: float = 0
    speed: float = 0
    eta: float = 0
    total: float = 0
    error: str = ""
    output: str = ""
    stage: str = ""

    @property
    def title(self):
        return self.info.get("title") or "Untitled"

    def transition(self, state: State):
        if state == self.state:
            return
        if state not in TRANSITIONS[self.state]:
            raise ValueError(f"Invalid transition: {self.state} → {state}")
        self.state = state

    def stage_path(self) -> Path:
        return Path(self.stage)
