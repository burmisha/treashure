from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DownloadTarget:
    url: str
    name: str
    custom_tags: dict[str, str] = field(default_factory=dict)
    output_path: Optional[str] = None

    @property
    def video_filename(self):
        return f'{self.name} - tmp.mp4'

    @property
    def audio_filename(self):
        return f'{self.name}.mp3'

    @property
    def result_filename(self):
        return f'{self.name}.mp4'

