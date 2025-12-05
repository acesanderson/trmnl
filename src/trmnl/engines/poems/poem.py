"""
Processing the KaggleHub dataset: tgdivy/poetry-foundation-poems
"""

from trmnl.engines.poems.process import process_poem, clean_title, Poem
import pandas as pd
from pathlib import Path
import random
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


async def random_poem() -> dict[str, str]:
    logger.info("Selecting a random poem from the dataset.")
    filtered_poems = filter_poems()
    poem_dict = random.choice(filtered_poems)
    poem_obj = Poem(**poem_dict)
    poem_text = ""
    new_poem_text = process_poem(poem_obj)
    if new_poem_text:
        poem_text = new_poem_text
    else:
        poem_text = poem_obj.poem
    title = clean_title(poem_obj.title)
    poet = poem_obj.poet
    return_dict = {
        "title": title.strip(),
        "poet": poet.strip(),
        "poem": poem_text.strip(),
    }
    return return_dict
