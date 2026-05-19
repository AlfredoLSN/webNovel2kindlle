from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chapter:
    title: str
    url: str
    number: int | None = None


@dataclass(frozen=True)
class Volume:
    title: str
    chapters: tuple[Chapter, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Novel:
    title: str
    url: str
    volumes: tuple[Volume, ...] = field(default_factory=tuple)

    @property
    def chapter_count(self) -> int:
        return sum(len(volume.chapters) for volume in self.volumes)
