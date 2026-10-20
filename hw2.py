#!/usr/bin/env python3
"""FTEC5660 HW2 student starter: build an agent that verifies CVs via MCP."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any


MCP_URL = "https://ftec5660.ngrok.app/mcp"
MODEL_NAME = "deepseek-v4-flash"
THRESHOLD = 0.5


def load_env_file(path: Path = Path(".env")) -> None:
    """Load the simple KEY=VALUE entries used by this homework."""
    if not path.is_file():
        return
    import os

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def cv_files(folder: Path) -> list[Path]:
    """Return PDFs directly inside *folder*, sorted numerically (CV_2 before CV_10)."""

    def key(path: Path) -> tuple[int, str]:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return (int(digits) if digits else math.inf, path.name)

    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
        key=key,
    )


def cv_text(path: Path) -> str:
    """Convert one CV PDF to markdown text."""
    from markitdown import MarkItDown

    return MarkItDown(enable_plugins=False).convert(str(path)).text_content


async def load_mcp_tools() -> list[Any]:
    """Connect to the course MCP server and return its tools as LangChain tools."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "social_graph": {
                "transport": "http",
                "url": MCP_URL,
                "headers": {"ngrok-skip-browser-warning": "true"},
            }
        }
    )
    return await client.get_tools()


def build_agent(tools: list[Any]) -> Any:
    """Create and return your agent once."""
    from langchain_deepseek import ChatDeepSeek
    from langchain.agents import create_agent

    model = ChatDeepSeek(
        model=MODEL_NAME,
        temperature=0,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
    )

    system_prompt = (
        "You are a strict CV verification agent for KYC.\n"
        "You are given one CV text. Verify its claims against the candidate's "
        "LinkedIn profile (primary source) and Facebook profile, using the tools.\n\n"
        "Steps:\n"
        "1. Extract the candidate's name and city from the CV.\n"
        "2. Call search_linkedin_people with the name and location to find the right person. "
        "Names are shared by many people, so use location (and industry if available) to disambiguate.\n"
        "3. Call get_linkedin_profile on the chosen person_id.\n"
        "4. Compare ONLY these fields: name, city, jobs (company, title, seniority, start_year, end_year), "
        "education (school, degree, field, graduation year), skills.\n\n"
        "Rules:\n"
        "- Wording differences are NOT discrepancies: 'BSc' vs 'Bachelor of Science', "
        "'UI/UX' vs 'UI/UX Design', a title matching the profile's seniority level.\n"
        "- Listing FEWER skills on the CV than the profile is NOT a discrepancy.\n"
        "- A discrepancy is any of: inflated job title, shifted employment or graduation year, "
        "upgraded degree, fake school or employer, wrong city, or a skill the CV claims but "
        "the profile does not have.\n"
        "- Job descriptions, headline and hometown are NEVER a source of discrepancy.\n\n"
        "After verification, output ONLY a single number between 0 and 1, nothing else.\n"
        "Use 0.9 if there is no discrepancy. Use 0.1 if there is at least one discrepancy.\n"
        "If you cannot find the person or verify, output 0.5."
    )

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )
    return agent


async def score_cvs(agent: Any, cvs: dict[str, str]) -> dict[str, float | None]:
    """Run your agent and return one reliability score per CV."""
    sem = asyncio.Semaphore(3)

    async def one(name: str, text: str) -> tuple[str, float | None]:
        async with sem:
            try:
                prompt = (
                    f"CV file name: {name}\n"
                    "Verify the following CV against the candidate's LinkedIn profile. "
                    "Output only one number in [0, 1].\n\n"
                    "----- CV START -----\n"
                    f"{text}\n"
                    "----- CV END -----"
                )
                resp = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt}]}
                )
                content = resp["messages"][-1].content

                if isinstance(content, list):
                    content = " ".join(
                        str(part.get("text", "")) if isinstance(part, dict) else str(part)
                        for part in content
                    )

                # 抓取 0~1 之间的数，优先取最后一个
                matches = re.findall(
                    r"(?<!\d)(?:0(?:\.\d+)?|1(?:\.0+)?)(?!\d)", str(content)
                )
                if matches:
                    score = float(matches[-1])
                    return name, max(0.0, min(1.0, score))
                return name, 0.5
            except Exception:
                return name, 0.5

    results = await asyncio.gather(*(one(n, t) for n, t in cvs.items()))
    return dict(results)


# Everything below is provided runner/scoring code. No edits are needed.

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_score(value: Any) -> float | None:
    """Accept a float/int, or text containing exactly one number, in [0, 1]."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        score = float(value)
    else:
        text = str(getattr(value, "content", value))
        matches = _NUMBER_RE.findall(text)
        if len(matches) != 1:
            return None
        score = float(matches[0])
    if math.isnan(score) or not 0.0 <= score <= 1.0:
        return None
    return score


def read_ground_truth(folder: Path) -> dict[str, dict[str, Any]]:
    """Read labels (1 = valid CV, 0 = has discrepancy) and reasons from the test folder."""
    path = folder / "ground_truth.json"
    if not path.is_file():
        return {}
    return {
        name: entry if isinstance(entry, dict) else {"label": entry}
        for name, entry in json.loads(path.read_text(encoding="utf-8")).items()
    }


def correctness_text(score: float | None, expected: dict[str, Any] | None) -> str:
    """Return `correct`, or an expected/predicted mismatch explanation."""
    if score is None:
        return "incorrect: score is missing or not a number in [0, 1]"
    if expected is None:
        return "not graded: no ground truth for this CV"
    label = int(expected["label"])
    predicted = 1 if score > THRESHOLD else 0
    if predicted == label:
        return "correct"
    reason = f" ({expected['reason']})" if expected.get("reason") else ""
    return f"incorrect: expected {label}{reason}, predicted {predicted}"


def write_results(names: list[str], scores: dict[str, Any], truth: dict[str, dict[str, Any]]) -> tuple[Path, int]:
    """Write the required results.csv file and return how many CVs were correct."""
    output = Path("results.csv")
    correct = 0
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cv", "score", "correctness"])
        for name in names:
            score = parse_score(scores.get(name))
            verdict = correctness_text(score, truth.get(name))
            correct += verdict == "correct"
            writer.writerow([name, "" if score is None else f"{score:.4f}", verdict])
    return output, correct


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FTEC5660 HW2 on CV PDFs")
    parser.add_argument(
        "--cv-folder",
        required=True,
        type=Path,
        help="folder containing CV PDF files",
    )
    return parser.parse_args()


async def run(folder: Path) -> int:
    paths = cv_files(folder)
    if not paths:
        raise SystemExit(f"no PDF files found in {folder}")

    load_env_file()
    cvs = {path.name: cv_text(path) for path in paths}
    tools = await load_mcp_tools()
    agent = build_agent(tools)
    scores = await score_cvs(agent, cvs)
    if not isinstance(scores, dict):
        raise TypeError("score_cvs() must return a dictionary")

    truth = read_ground_truth(folder)
    output, correct = write_results(list(cvs), scores, truth)
    summary = f" Accuracy: {correct}/{len(cvs)}." if truth else ""
    print(f"Processed {len(cvs)} CV(s). Wrote {output}.{summary}")
    return 0


def main() -> int:
    args = parse_args()
    if not args.cv_folder.is_dir():
        raise SystemExit(f"not a folder: {args.cv_folder}")
    return asyncio.run(run(args.cv_folder))


if __name__ == "__main__":
    raise SystemExit(main())
