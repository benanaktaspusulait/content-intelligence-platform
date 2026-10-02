from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POMPOM_")

    # Absolute default derived from this source file so the service does not
    # depend on the process working directory. parents[2] == the project root
    # that contains the shared ``data/`` directory (ml-service/app -> ml-service
    # -> Pompom_Creative_Intelligence).
    data_root: Path = Path(__file__).resolve().parents[2] / "data"
    analysis_version: str = "video-analysis-v1"

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


settings = Settings()
