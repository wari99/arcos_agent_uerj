import os
from datetime import datetime
from tools.commons.core import logger


def get_current_date() -> dict:
    """Get the current date in the format YYYY-MM-DD."""
    return {"current_date": datetime.now().strftime("%Y-%m-%d")}


def load_prompt_from_markdown(prompts_dir: str) -> str:
    """Load and join markdown prompt files from a directory.

    Loads all .md files from the specified directory, sorted by filename.
    Files should be named with numeric prefixes for ordering:
    - 00-intro.md
    - 01-capabilities.md
    - 02-tools.md
    - etc.

    Parameters
    ----------
    prompts_dir : str
        Absolute path to the directory containing .md files

    Returns
    -------
    str
        Combined prompt text with files joined by double newlines

    Raises
    ------
    FileNotFoundError
        If prompts_dir doesn't exist
    ValueError
        If no .md files found in directory
    """
    if not os.path.exists(prompts_dir):
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

    if not os.path.isdir(prompts_dir):
        raise NotADirectoryError(f"Path is not a directory: {prompts_dir}")

    md_files = sorted([f for f in os.listdir(prompts_dir) if f.endswith(".md")])

    if not md_files:
        raise ValueError(f"No .md files found in directory: {prompts_dir}")

    logger.info(f"Loading {len(md_files)} prompt files from {prompts_dir}")

    prompt_parts = []
    for md_file in md_files:
        filepath = os.path.join(prompts_dir, md_file)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                prompt_parts.append(content)
                logger.debug(f"Loaded prompt file: {md_file}")
        except Exception as e:
            logger.error(f"Error reading {md_file}: {e}")
            raise

    combined_prompt = "\n\n".join(prompt_parts)
    logger.info(
        f"Combined prompt: {len(combined_prompt)} characters from {len(md_files)} files"
    )

    return combined_prompt