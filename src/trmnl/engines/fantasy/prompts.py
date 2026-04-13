# src/trmnl/engines/fantasy/prompts.py
from __future__ import annotations

STYLE_PREAMBLE = (
    "Albrecht Dürer woodcut engraving style, black and white only, "
    "fine crosshatching, stark contrast, dramatic chiaroscuro, no color, "
    "no gradients, 16th century German Renaissance printmaking aesthetic —"
)

PROMPTS: list[dict[str, str]] = [
    {"slug": "dragon_hoard", "prompt": "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"},
    {"slug": "knight_forest", "prompt": "an armored knight on horseback pausing at the edge of a dark enchanted forest"},
    {"slug": "wizard_tower", "prompt": "a wizard's tower on a cliff edge at night, lit windows, storm clouds gathering"},
    {"slug": "sea_serpent", "prompt": "a sea serpent emerging from stormy waves to inspect a small fishing vessel"},
    {"slug": "gryphon_nest", "prompt": "a gryphon tending to its nest of eggs on a mountain peak"},
    {"slug": "dungeon_map", "prompt": "a detailed overhead map of a dungeon with traps, treasure rooms, and a dragon's lair"},
    {"slug": "alchemy_lab", "prompt": "an alchemist's laboratory cluttered with retorts, skulls, astrolabes, and bubbling flasks"},
    {"slug": "faerie_market", "prompt": "a midnight market under a bridge where fae creatures barter strange goods"},
    {"slug": "undead_army", "prompt": "a skeletal army marching through a ruined city at dusk, led by a lich king"},
    {"slug": "forest_witch", "prompt": "a witch's cottage deep in the woods, smoke rising from the chimney, herbs drying in the doorway"},
    {"slug": "siege_castle", "prompt": "a trebuchet launching stones at a castle gate while defenders pour boiling oil from battlements"},
    {"slug": "tavern_brawl", "prompt": "a chaotic tavern brawl, men thrown over tables, tankards flying, a bard still playing in the corner"},
    {"slug": "phoenix_rising", "prompt": "a phoenix erupting from ashes above a ruined temple, wings spread wide"},
    {"slug": "dwarven_forge", "prompt": "dwarven smiths hammering glowing metal in a vast underground forge lit by magma"},
    {"slug": "elven_council", "prompt": "an elven council meeting in a great hollow tree, ancient figures gesturing over a glowing map"},
    {"slug": "demon_summoning", "prompt": "a robed figure drawing a pentagram on a stone floor as a demon begins to materialize from smoke"},
    {"slug": "sea_voyage", "prompt": "a galleon with tattered sails navigating between enormous sea stacks in thick fog"},
    {"slug": "dragon_duel", "prompt": "two dragons locked in aerial combat above a burning village"},
    {"slug": "oracle_vision", "prompt": "a blind oracle seated at a smoking brazier, her face illuminated, pointing into darkness"},
    {"slug": "giant_chess", "prompt": "two giants playing chess with human knights as pieces in an ancient ruined hall"},
]
