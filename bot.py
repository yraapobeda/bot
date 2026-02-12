from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Config:
    bot_token: str

def load_config() -> Config:
    return Config("7728266567:AAFq2qKO9qxsPtB4jULrXCOK3LjCbvmLDso")