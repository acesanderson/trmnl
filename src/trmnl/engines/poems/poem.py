"""
Processing the KaggleHub dataset: tgdivy/poetry-foundation-poems
"""

from trmnl.engines.poems.process import process_poem, clean_title, Poem
import pandas as pd
from pathlib import Path
import random
import logging
from functools import cache
from Levenshtein import distance

logger = logging.getLogger(__name__)

dataset = Path(
    "/home/bianders/.cache/kagglehub/datasets/tgdivy/poetry-foundation-poems/versions/1/PoetryFoundationData.csv"
).expanduser()

df = pd.read_csv(dataset)

poets = [
    "Alexander Pope",
    "Alfred, Lord Tennyson",
    "Algernon Charles Swinburne",
    "Andrew Marvell",
    "Anna Lætitia Barbauld",
    "Anne Carson",
    "Anne Sexton",
    "Annie Finch",
    "Aphra Behn",
    "Basil Bunting",
    "Ben Jonson",
    "Carl Phillips",
    "Charlotte Smith",
    "Christina Rossetti",
    "Christopher Marlowe",
    "Claudia Rankine",
    "D. H. Lawrence",
    "Dante Gabriel Rossetti",
    "Dylan Thomas",
    "E. E. Cummings",
    "Edith Sitwell",
    "Edmund Spenser",
    "Elizabeth Barrett Browning",
    "Elizabeth Bishop",
    "Emily Brontë",
    "Emily Dickinson",
    "Ezra Pound",
    "Frank Bidart",
    "Franz Wright",
    "Galway Kinnell",
    "Geoffrey Hill",
    "George Herbert",
    "Gerard Manley Hopkins",
    "H. D.",
    "Hart Crane",
    "Henry Vaughan",
    "James Wright",
    "Jean Valentine",
    "John Berryman",
    "John Clare",
    "John Donne",
    "John Dryden",
    "John Keats",
    "John Milton",
    "Jonathan Swift",
    "Jorie Graham",
    "Larry Levis",
    "Leigh Hunt",
    "Letitia Elizabeth Landon",
    "Louise Glück",
    "Lucie Brock-Broido",
    "Marianne Moore",
    "Mary Robinson",
    "Matthew Arnold",
    "Mina Loy",
    "Monica Youn",
    "Natalie Diaz",
    "Ocean Vuong",
    "Oliver Goldsmith",
    "Paul Celan",
    "Percy Bysshe Shelley",
    "Philip Larkin",
    "R. S. Thomas",
    "Rainer Maria Rilke",
    "Richard Crashaw",
    "Robert Browning",
    "Robert Burns",
    "Robert Graves",
    "Robert Herrick",
    "Robert Lowell",
    "Robert Southey",
    "Samuel Johnson",
    "Samuel Taylor Coleridge",
    "Sir Philip Sidney",
    "Sir Walter Scott",
    "Sylvia Plath",
    "T. S. Eliot",
    "Thomas Carew",
    "Thomas Gray",
    "Thomas Hardy",
    "Thomas Moore",
    "W. S. Merwin",
    "Wallace Stevens",
    "William Blake",
    "William Butler Yeats",
    "William Carlos Williams",
    "William Collins",
    "William Cowper",
    "William Shakespeare",
    "William Wordsworth",
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


def fuzzy_match(
    target_poets: list[str],
    dataset_poets: list[str],
    threshold: int = 5,
) -> dict[str, list[tuple[str, int]]]:
    """
    Match target poets against dataset poets using Levenshtein distance.

    Returns dict mapping each target poet to list of (candidate, distance) tuples
    sorted by distance, filtered by threshold.
    """
    results = {}
    for target in target_poets:
        target_lower = target.lower()
        matches = []
        for candidate in dataset_poets:
            d = distance(target_lower, candidate.lower())
            if d <= threshold:
                matches.append((candidate, d))
        matches.sort(key=lambda x: x[1])
        results[target] = matches
    return results


def best_match(
    target_poets: list[str],
    dataset_poets: list[str],
) -> dict[str, tuple[str, int] | None]:
    """Return only the best match for each target poet."""
    results = {}
    for target in target_poets:
        target_lower = target.lower()
        best = None
        best_dist = float("inf")
        for candidate in dataset_poets:
            d = distance(target_lower, candidate.lower())
            if d < best_dist:
                best = candidate
                best_dist = d
        results[target] = (best, best_dist) if best else None
    return results


def identify_missing_poets():
    """
    Identify poets from poet_list that are not present in dataset_df.
    Prints the number of missing poets and their fuzzy matches.
    """
    # Find all the poets from our list who are NOT in the dataset
    missing_poets = [poet for poet in poets if poet not in df["Poet"].unique()]
    target = missing_poets
    print(f"MISSING POETS: {len(missing_poets)}")

    # Example usage
    dataset = df["Poet"].unique().tolist()

    print("All matches within threshold:")
    for poet, matches in fuzzy_match(target, dataset).items():
        print(f"  {poet}: {matches}")

    print("\nBest matches:")
    for poet, match in best_match(target, dataset).items():
        print(f"  {poet} -> {match}")
