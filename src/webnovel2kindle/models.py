from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chapter:
    title: str
    url: str
    number: int | None = None


@dataclass(frozen=True)
class ChapterContent:
    title: str
    html: str


@dataclass(frozen=True)
class Volume:
    title: str
    chapters: tuple[Chapter, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NovelMetadata:
    author: str | None = None
    status: str | None = None
    novel_type: str | None = None
    release_year: str | None = None
    posted_at: str | None = None
    updated_at: str | None = None
    description: str | None = None
    cover_url: str | None = None
    genres: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Novel:
    title: str
    url: str
    volumes: tuple[Volume, ...] = field(default_factory=tuple)
    metadata: NovelMetadata = field(default_factory=NovelMetadata)

    @property
    def chapter_count(self) -> int:
        return sum(len(volume.chapters) for volume in self.volumes)
