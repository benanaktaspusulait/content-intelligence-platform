from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POMPOM_")

    # Absolute default derived from this source file so the service does not
    # depend on the process working directory. parents[2] == the project root
    # that contains the shared ``data/`` directory (ml-service/app -> ml-service
    # -> Pompom_Creative_Intelligence).
    data_root: Path = Path(__file__).resolve().parents[2] / "data"
    analysis_version: str = "sampled-visual-motion-v4"
    parser_version: str = "prompt-parser-v2"
    rule_engine_version: str = "quality-rule-engine-v2"
    # No producibility_validator_version setting: AI producibility validation
    # (PRODUCIBILITY_001/002/003) is a family of ordinary deterministic rules
    # in the versioned ruleset, already fully identified by the ruleset
    # version itself. There is no independent "producibility validator"
    # runtime to version separately - populating this with any string
    # (including a copy of the ruleset version) would fabricate a second
    # version axis for something that is not architecturally separate. See
    # PART_01_COMPLETION_ROADMAP.md's Plan C1.

    @property
    def rules_dir(self) -> Path:
        return self.data_root / "rules"

    @property
    def golden_sets_dir(self) -> Path:
        return self.data_root / "golden_sets"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_root / "model-artifacts"

    @property
    def test_cases_dir(self) -> Path:
        return self.data_root / "test_cases"

    semantic_target_frames: int = 8
    semantic_max_frames: int = 14
    semantic_frame_cache_enabled: bool = True


settings = Settings()
