from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_dir: Path
    input_dir: Path
    data_dir: Path
    database: Path
    host: str = "127.0.0.1"
    port: int = 8765
    analysis_version: str = "0.1.0"
    rubric_version: str = "pompom-action-dna-v1"
    vision_provider: str = "heuristic"
    vision_base_url: str = "http://127.0.0.1:11434/v1"
    vision_model: str = ""
    external_network_enabled: bool = False
    transcription_enabled: bool = False
    sample_fps: float = 4.0
    max_analysis_width: int = 480
    performance_bands: dict[str, int] = field(default_factory=dict)


def load_settings(config_path: str | Path | None = None) -> Settings:
    project_dir = Path(__file__).resolve().parent.parent
    path = Path(config_path).resolve() if config_path else project_dir / "config.toml"
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    def resolved(key: str) -> Path:
        value = Path(raw[key]).expanduser()
        return value.resolve() if value.is_absolute() else (project_dir / value).resolve()

    settings = Settings(
        project_dir=project_dir,
        input_dir=resolved("input_dir"),
        data_dir=resolved("data_dir"),
        database=resolved("database"),
        host=str(raw.get("host", "127.0.0.1")),
        port=int(raw.get("port", 8765)),
        analysis_version=str(raw.get("analysis_version", "0.1.0")),
        rubric_version=str(raw.get("rubric_version", "pompom-action-dna-v1")),
        vision_provider=os.getenv("VISION_PROVIDER", str(raw.get("vision_provider", "heuristic"))),
        vision_base_url=os.getenv("VISION_BASE_URL", str(raw.get("vision_base_url", ""))),
        vision_model=os.getenv("VISION_MODEL", str(raw.get("vision_model", ""))),
        external_network_enabled=bool(raw.get("external_network_enabled", False)),
        transcription_enabled=bool(raw.get("transcription_enabled", False)),
        sample_fps=float(raw.get("sample_fps", 4.0)),
        max_analysis_width=int(raw.get("max_analysis_width", 480)),
        performance_bands={k: int(v) for k, v in raw.get("performance_bands", {}).items()},
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
