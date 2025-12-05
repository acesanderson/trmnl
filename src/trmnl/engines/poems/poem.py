"""
Processing the KaggleHub dataset: tgdivy/poetry-foundation-poems
"""

import pandas as pd
from pathlib import Path
import random
import re
import logging
from functools import cache

logger = logging.getLogger(__name__)

dataset = Path(
    "/home/bianders/.cache/kagglehub/datasets/tgdivy/poetry-foundation-poems/versions/1/PoetryFoundationData.csv"
).expanduser()

df = pd.read_csv(dataset)

poets = [
    "William Carlos Williams",
    "Ezra Pound",
    "T. S. Eliot",
    "Elizabeth Bishop",
    "H.D.",
    "Marianne Moore",
    "Philip Larkin",
    "William Butler Yeats",
    "Wallace Stevens",
    "Dylan Thomas",
    "Ted Hughes",
    "Robert Graves",
    "D.H. Lawrence",
]


@cache
def filter_poems(min_chars=100, max_chars=800) -> list[dict[str, str]]:
    mask = (
        df["Poet"].isin(pd.Series(poets))
        & (df["Poem"].str.len() <= max_chars)
        & (df["Poem"].str.len() >= min_chars)
    )
    filtered = df.loc[mask, ["Poet", "Poem", "Title"]]
    return filtered.rename(
        columns={"Poet": "poet", "Poem": "poem", "Title": "title"}
    ).to_dict("records")


def clean_poem_text(text: str) -> str:
    """Normalize line breaks and whitespace in poem text."""
    # Normalize all line break variants to \n
    text = text.replace("\r\r\n", "\n")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Multiple spaces (3+) likely represent line breaks
    text = re.sub(r"  {2,}", "\n", text)

    # Collapse 3+ newlines into double (stanza break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def clean_title(title: str) -> str:
    """Collapse all whitespace in title."""
    return " ".join(title.split()).strip()


async def random_poem() -> dict[str, str]:
    logger.info("Selecting a random poem from the dataset.")
    filtered_poems = filter_poems()
    poem = random.choice(filtered_poems)
    poem_text = clean_poem_text(poem["poem"])
    title = clean_title(poem["title"])
    poet = poem["poet"]
    return_dict = {
        "title": title.strip(),
        "poet": poet.strip(),
        "poem": poem_text.strip(),
    }
    return return_dict
