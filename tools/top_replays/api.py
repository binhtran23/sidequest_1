"""Kaggle API adapter and pure cohort-selection helpers."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Protocol


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, obj.get(_camel(name), default))
    return getattr(obj, name, default)


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(item.title() for item in tail)


def text_value(obj: Any) -> str | None:
    if obj is None:
        return None
    raw = getattr(obj, "name", obj)
    return str(raw)


def timestamp_value(obj: Any) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(obj)


def score_value(score: Any) -> Decimal:
    try:
        return Decimal(str(score).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid leaderboard score: {score!r}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReplayClient(Protocol):
    def leaderboard(self, competition: str, count: int) -> Iterable[Any]: ...
    def team_submissions(self, team_id: int) -> Iterable[Any]: ...
    def submission_episodes(self, submission_id: int) -> Iterable[Any]: ...
    def download_replay(self, episode_id: int, directory: Path) -> Path: ...


class KaggleReplayClient:
    """Authenticated adapter over Kaggle CLI's supported Python API."""

    def __init__(self) -> None:
        from kaggle.api.kaggle_api_extended import KaggleApi

        self.api = KaggleApi()
        self.api.authenticate()

    def leaderboard(self, competition: str, count: int) -> Iterable[Any]:
        return self.api.competition_leaderboard_view(competition, page_size=count) or []

    def team_submissions(self, team_id: int) -> Iterable[Any]:
        return self.api.competition_team_submissions(team_id) or []

    def submission_episodes(self, submission_id: int) -> Iterable[Any]:
        return self.api.competition_list_episodes(submission_id) or []

    def download_replay(self, episode_id: int, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        self.api.competition_episode_replay(episode_id, path=str(directory), quiet=True)
        return directory / f"episode-{episode_id}-replay.json"


def select_scoring_submission(leaderboard_row: Any, submissions: Iterable[Any]) -> dict[str, Any]:
    """Match displayed score to one active, public-safe submission.

    Score equality is decimal rather than floating point.  A rare equal-score tie
    is resolved by the leaderboard submission timestamp and then latest active
    submission ID, making fixture and live selection stable.
    """
    target_score = score_value(value(leaderboard_row, "score"))
    target_date = timestamp_value(value(leaderboard_row, "submission_date"))
    matches = []
    for submission in submissions:
        public_score = value(submission, "public_score")
        if public_score is None or score_value(public_score) != target_score:
            continue
        submitted = timestamp_value(value(submission, "date_submitted"))
        matches.append(
            {
                "submission_id": int(value(submission, "id")),
                "date_submitted": submitted,
                "public_score": str(public_score),
                "date_matches_leaderboard": submitted == target_date,
            }
        )
    if not matches:
        raise ValueError(
            f"team {value(leaderboard_row, 'team_id')} has no active submission "
            f"matching leaderboard score {value(leaderboard_row, 'score')!r}"
        )
    matches.sort(
        key=lambda item: (
            item["date_matches_leaderboard"],
            item["date_submitted"] or "",
            item["submission_id"],
        ),
        reverse=True,
    )
    return matches[0]


def _is_completed_public(episode: Any) -> bool:
    state = (text_value(value(episode, "state")) or "").upper()
    episode_type = (text_value(value(episode, "type")) or "").upper()
    completed = not state or state.endswith("COMPLETED") or state.endswith("COMPLETE")
    public = not episode_type or episode_type.endswith("PUBLIC")
    return completed and public


def seat_for_submission(episode: Any, submission_id: int, team_id: int | None = None) -> int:
    matches = []
    for agent in value(episode, "agents", []) or []:
        if int(value(agent, "submission_id", -1)) != int(submission_id):
            continue
        if team_id is not None and int(value(agent, "team_id", -1)) != int(team_id):
            continue
        matches.append(int(value(agent, "index")))
    if len(matches) != 1:
        raise ValueError(
            f"episode {value(episode, 'id')} has {len(matches)} seats for "
            f"submission {submission_id}, team {team_id}"
        )
    return matches[0]


def select_latest_episodes(
    episodes: Iterable[Any], submission_id: int, team_id: int, count: int
) -> list[Any]:
    eligible = []
    seen = set()
    for episode in episodes:
        episode_id = int(value(episode, "id"))
        if episode_id in seen or not _is_completed_public(episode):
            continue
        seat_for_submission(episode, submission_id, team_id)
        seen.add(episode_id)
        eligible.append(episode)
    eligible.sort(
        key=lambda episode: (
            timestamp_value(value(episode, "end_time")) or "",
            int(value(episode, "id")),
        ),
        reverse=True,
    )
    if len(eligible) < count:
        raise ValueError(
            f"submission {submission_id} exposes only {len(eligible)} completed public "
            f"episodes; {count} required"
        )
    return eligible[:count]


def agent_record(agent: Any) -> dict[str, Any]:
    return {
        "submission_id": int(value(agent, "submission_id", 0)),
        "seat": int(value(agent, "index", 0)),
        "reward": float(value(agent, "reward", 0.0)),
        "state": text_value(value(agent, "state")),
        "team_name": str(value(agent, "team_name", "")),
        "team_id": int(value(agent, "team_id", 0)),
    }


def capture_cohort(
    client: ReplayClient,
    competition: str,
    top: int,
    games_per_team: int,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Resolve a frozen leaderboard-to-submission-to-episode cohort."""
    rows = list(client.leaderboard(competition, top))
    if len(rows) < top:
        raise ValueError(f"leaderboard returned {len(rows)} teams; {top} required")
    cohort = []
    associations = []
    for rank, row in enumerate(rows[:top], start=1):
        team_id = int(value(row, "team_id"))
        selected = select_scoring_submission(row, client.team_submissions(team_id))
        episodes = select_latest_episodes(
            client.submission_episodes(selected["submission_id"]),
            selected["submission_id"],
            team_id,
            games_per_team,
        )
        team = {
            "rank": rank,
            "team_id": team_id,
            "team_name": str(value(row, "team_name", "")),
            "leaderboard_score": str(value(row, "score")),
            "leaderboard_submission_date": timestamp_value(value(row, "submission_date")),
            **selected,
            "episode_ids": [int(value(episode, "id")) for episode in episodes],
        }
        cohort.append(team)
        for episode in episodes:
            agents = sorted(
                (agent_record(agent) for agent in (value(episode, "agents", []) or [])),
                key=lambda item: item["seat"],
            )
            seat = seat_for_submission(episode, selected["submission_id"], team_id)
            opponent = next((agent for agent in agents if agent["seat"] != seat), None)
            episode_id = int(value(episode, "id"))
            associations.append(
                {
                    "association_id": f"{team_id}:{selected['submission_id']}:{episode_id}",
                    "episode_id": episode_id,
                    "rank": rank,
                    "team_id": team_id,
                    "team_name": team["team_name"],
                    "leaderboard_score": team["leaderboard_score"],
                    "submission_id": selected["submission_id"],
                    "seat": seat,
                    "opponent_team_id": opponent["team_id"] if opponent else None,
                    "opponent_team_name": opponent["team_name"] if opponent else None,
                    "opponent_submission_id": opponent["submission_id"] if opponent else None,
                    "create_time": timestamp_value(value(episode, "create_time")),
                    "end_time": timestamp_value(value(episode, "end_time")),
                    "episode_state": text_value(value(episode, "state")),
                    "episode_type": text_value(value(episode, "type")),
                    "agents": agents,
                }
            )
    return {
        "captured_at": captured_at or utc_now(),
        "competition": competition,
        "top": top,
        "games_per_team": games_per_team,
        "teams": cohort,
        "associations": associations,
    }


def ensure_replay(
    client: ReplayClient,
    evidence_dir: Path,
    episode_id: int,
    expected: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Verify or atomically create immutable evidence for one episode.

    Existing mismatched evidence is never replaced.  Downloads go to a sibling
    temporary directory and become visible only after JSON validation succeeds.
    """
    evidence_dir.mkdir(parents=True, exist_ok=True)
    target = evidence_dir / f"episode-{episode_id}-replay.json"
    if target.exists():
        digest = sha256_file(target)
        size = target.stat().st_size
        if expected and (digest != expected.get("sha256") or size != expected.get("byte_size")):
            raise ValueError(f"immutable evidence mismatch: {target}")
        json.loads(target.read_text())
        target.chmod(0o444)
        downloaded_at = (expected or {}).get("downloaded_at")
        if downloaded_at is None:
            downloaded_at = timestamp_value(datetime.fromtimestamp(target.stat().st_mtime, timezone.utc))
        return {
            "episode_id": episode_id,
            "path": str(target),
            "sha256": digest,
            "byte_size": size,
            "downloaded_at": downloaded_at,
        }, False

    temp_dir = Path(tempfile.mkdtemp(prefix=f"episode-{episode_id}-", dir=evidence_dir))
    try:
        downloaded = client.download_replay(episode_id, temp_dir)
        if not downloaded.is_file():
            raise ValueError(f"Kaggle returned no replay file for episode {episode_id}")
        json.loads(downloaded.read_text())
        digest = sha256_file(downloaded)
        size = downloaded.stat().st_size
        if target.exists():
            raise FileExistsError(f"evidence appeared concurrently: {target}")
        os.replace(downloaded, target)
        target.chmod(0o444)
        return {
            "episode_id": episode_id,
            "path": str(target),
            "sha256": digest,
            "byte_size": size,
            "downloaded_at": utc_now(),
        }, True
    finally:
        for child in temp_dir.iterdir():
            child.unlink()
        temp_dir.rmdir()
