from conduit.core.prompt.prompt_loader import PromptLoader
from conduit.config import settings
from conduit.remote import (
    RemoteModelAsync,
    GenerationParams,
    ConduitOptions,
    GenerationRequest,
)
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
PARAMS = GenerationParams(model="gpt-oss:latest")
OPTIONS = ConduitOptions(project_name="trmnl", cache=settings.default_cache("trmnl"))
model_name = "gpt-oss:latest"
model = RemoteModelAsync("gpt-oss:latest")


def clean_poem_text(text: str) -> str:
    """Normalize line breaks and whitespace in poem text."""
    text = text.replace("\r\r\n", "\n")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"  {2,}", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()


def clean_title(title: str) -> str:
    return " ".join(title.split()).strip()


async def _restore_poem(poem: Poem) -> str:
    """
    If LLM knows the poem, it will restore it.
    """
    prompt = pl["expert"]
    rendered = prompt.render(input_variables=poem.model_dump())
    request = GenerationRequest.from_query_input(rendered, PARAMS, OPTIONS)
    response = await model.query(request)
    return str(response.content)


async def _reconstruct_poem(poem: Poem) -> str:
    """
    If LLM doesn't know the poem, it use its judgment.
    """
    logger.info("Reconstructing poem.")
    prompt = pl["forensic"]
    rendered = prompt.render(input_variables=poem.model_dump())
    request = GenerationRequest.from_query_input(rendered, PARAMS, OPTIONS)
    response = await model.query(request)
    return str(response.content)


async def _route_poem(poem: Poem) -> Literal["restore", "reconstruct"]:
    prompt = pl["route"]
    rendered = prompt.render(input_variables=poem.model_dump())
    request = GenerationRequest.from_query_input(rendered, PARAMS, OPTIONS)
    response = await model.query(request)
    response_string = str(response.content).strip().lower()
    if response_string == "no":
        return "reconstruct"
    elif response_string == "yes":
        return "restore"
    else:
        raise ValueError(f"Unexpected routing response: {response_string}")


def _needs_restoration(text: str) -> bool:
    logger.info("Restoring poem.")
    lines = text.split("\n")
    if len(lines) < 3:
        return True
    longest_line = max(len(line) for line in lines)
    if longest_line > 65:
        return True
    return False


async def process_poem(poem: Poem) -> str | None:
    if not _needs_restoration(poem.poem):
        return None

    logger.info("Poem needs restoration/reconstruction.")

    route = await _route_poem(poem)

    match route:
        case "restore":
            return await _restore_poem(poem)
        case "reconstruct":
            return await _reconstruct_poem(poem)
