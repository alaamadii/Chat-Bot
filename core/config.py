"""Load local configuration before modules capture environment settings."""

from pathlib import Path

from dotenv import load_dotenv


# Process environment always wins; resolve independently of the working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
