from pathlib import Path

import yaml
from pydantic import BaseModel

from efm.transaction import TransactionError, TransactionSuccess


class DbMeta(BaseModel):
    site_dirpath: Path
    edit_api_url: str | None


class Db(BaseModel):
    meta: DbMeta
    books: list[TransactionError | TransactionSuccess]

    def save(self, filepath: Path):
        filepath.write_text(yaml.dump(self.model_dump(mode="json")))
