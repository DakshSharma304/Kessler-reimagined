"""Service configuration shared by the HTTP and command-line interfaces."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    service: str = "Kessler"
    version: str = "0.1.0"
    cache_directory: Path = Path(os.environ.get("KESSLER_CACHE_DIR", ".cache/kessler"))


settings = Settings()
