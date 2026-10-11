"""Service configuration shared by the HTTP and command-line interfaces."""

from dataclasses import dataclass
from pathlib import Path
import os
import json
import ipaddress
import re
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    service: str = "Kessler"
    version: str = "0.1.0"
    cache_directory: Path = Path(os.environ.get("KESSLER_CACHE_DIR", ".cache/kessler"))
    data_directory: Path = Path('data')
    catalog_files: tuple[Path,...] = ()
    metadata_file: Path | None = None
    allowed_origins: tuple[str,...] = ('http://localhost:5173','http://127.0.0.1:5173','http://localhost:3000','http://127.0.0.1:3000')
    host: str = '127.0.0.1'
    port: int = 8000

    def __post_init__(self):
        if not isinstance(self.port,int) or isinstance(self.port,bool) or not 1<=self.port<=65535:
            raise ValueError('KESSLER_PORT must be an integer in 1..65535')
        try: ipaddress.ip_address(self.host)
        except ValueError:
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.\-]{0,252}',self.host):
                raise ValueError('KESSLER_HOST must be a hostname or IP address, not a URL')
        for origin in self.allowed_origins:
            if not isinstance(origin,str): raise ValueError('KESSLER_ALLOWED_ORIGINS must contain origin strings')
            parsed=urlsplit(origin)
            if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or '*' in origin:
                raise ValueError('KESSLER_ALLOWED_ORIGINS requires explicit HTTP(S) origins, without wildcard/path/credentials')
            try: parsed.port
            except ValueError as error: raise ValueError('Invalid frontend origin port') from error
        for path in (*self.catalog_files,*(() if self.metadata_file is None else (self.metadata_file,))):
            if not path.is_file(): raise ValueError(f'Configured data file does not exist: {path}')

    @classmethod
    def from_environment(cls):
        data=Path(os.environ.get('KESSLER_DATA_DIR','data'))
        def data_path(value):
            path=Path(value)
            return path if path.is_absolute() else data/path
        def array(name,default):
            try: values=json.loads(os.environ.get(name,json.dumps(default)))
            except json.JSONDecodeError as error: raise ValueError(f'{name} must be a JSON array') from error
            if not isinstance(values,list) or any(not isinstance(v,str) for v in values): raise ValueError(f'{name} must be a JSON array of strings')
            return values
        origins=[] if os.environ.get('KESSLER_ENV','development')=='production' else list(cls().allowed_origins)
        return cls(cache_directory=Path(os.environ.get('KESSLER_CACHE_DIR','.cache/kessler')),data_directory=data,
            catalog_files=tuple(data_path(v) for v in array('KESSLER_CATALOG_FILES',[])),
            metadata_file=data_path(os.environ['KESSLER_METADATA_FILE']) if os.environ.get('KESSLER_METADATA_FILE') else None,
            allowed_origins=tuple(array('KESSLER_ALLOWED_ORIGINS',origins)),
            host=os.environ.get('KESSLER_HOST','127.0.0.1'),port=int(os.environ.get('KESSLER_PORT','8000')))


settings = Settings.from_environment()
