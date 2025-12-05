from conduit.prompt.prompt_loader import PromptLoader
from conduit.remote import RemoteModel, Response
from pathlib import Path
from pydantic import BaseModel
from typing import Literal
import logging
import re

logger = logging.getLogger(__name__)


class Poem(BaseModel):
    poet: str
    title: str
    poem: str

    def model_post_init(self, context):
        self.poem = clean_poem_text(self.poem)
        self.title = clean_title(self.title)


PROMPTS_DIR = Path(__file__).parent / "prompts"
pl = PromptLoader(PROMPTS_DIR)
model = RemoteModel("gpt-oss:latest")


# Programmatic text cleaning
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


# LLM-based processing
def _restore_poem(poem: Poem) -> str:
    """
    If LLM knows the poem, it will restore it.
    """
    prompt = pl["expert"]
    rendered = prompt.render(input_variables=poem.model_dump())
    response = model.query(rendered)
    assert isinstance(response, Response)
    return str(response.content)


def _reconstruct_poem(poem: Poem) -> str:
    """
    If LLM doesn't know the poem, it use its judgment. (Lord help us.)
    """
    logger.info("Reconstructing poem.")
    prompt = pl["forensic"]
    rendered = prompt.render(input_variables=poem.model_dump())
    response = model.query(rendered)
    assert isinstance(response, Response)
    return str(response.content)


def _route_poem(poem: Poem) -> Literal["restore", "reconstruct"]:
    prompt = pl["route"]
    rendered = prompt.render(input_variables=poem.model_dump())
    response = model.query(rendered)
    assert isinstance(response, Response)
    response_string = str(response.content).strip().lower()
    if response_string == "no":
        return "reconstruct"
    elif response_string == "yes":
        return "restore"
    else:
        raise ValueError(f"Unexpected routing response: {response_string}")


def _needs_restoration(text: str) -> bool:
    """
    Returns True if the poem looks 'flattened' (prose-like).
    """
    logger.info("Restoring poem.")
    lines = text.split("\n")

    # Check 1: Is it just a single blob?
    # (Allowing 2 lines accounts for accidental title inclusion)
    if len(lines) < 3:
        return True

    # Check 2: Are the lines unnaturally long?
    # 65 chars is a safe threshold for poetry vs prose
    longest_line = max(len(line) for line in lines)
    if longest_line > 65:
        return True

    return False


def process_poem(poem: Poem) -> str | None:
    # See if we need it
    if not _needs_restoration(poem.poem):
        return
    logger.info("Poem needs restoration/reconstruction.")
    # Poem is janky! Let's fix it.
    route = _route_poem(poem)
    match route:
        case "restore":
            return _restore_poem(poem)
        case "reconstruct":
            return _reconstruct_poem(poem)
