import json
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

from tools.top_replays.api import (
    capture_cohort,
    ensure_replay,
    select_latest_episodes,
    select_scoring_submission,
    sha256_file,
)
from tools.top_replays.normalize import (
    ReplayValidationError,
    _route_row,
    _turn_rows,
    load_replay,
    normalize_snapshot,
    validate_referential_integrity,
)
from tools.top_replays.routing import Waypoint, optimise_route


def agent(submission_id, seat, team_id, name, reward=0.0):
    return {
        "submissionId": submission_id, "index": seat, "teamId": team_id,
        "teamName": name, "reward": float(reward), "state": "COMPLETE",
    }


def episode(episode_id, end, agents):
    return {
        "id": episode_id, "createTime": "2026-09-10T00:00:00Z", "endTime": end,
        "state": "COMPLETED", "type": "EPISODE_TYPE_PUBLIC", "agents": agents,
    }


def farm(money=100.0, farmer=(4, 4), hands=None, tile=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if tile is not None:
        tiles[farmer[1]][farmer[0]] = tile
    return {
        "money": money, "farmer": list(farmer), "hands": [list(item) for item in (hands or [])],
        "tiles": tiles, "unlocked_quadrants": ["NW"], "hires_today": len(hands or []),
    }


def observation(seat, farms, private, step, day=0, hour=0):
    return {
        "player": seat, "step": step, "day": day, "hour": hour, "farms": farms,
        "private": private,
        "market": {"inventory": {"WHEAT": 10000}, "prices": {"WHEAT": 25}},
        "town": {"unlocked_shops": []},
    }


def small_replay():
    farms0 = [farm(), farm(money=200.0)]
    farms1 = [farm(), farm(money=199.0, hands=[(4, 4)])]
    private0 = {"shed": {"WHEAT": 11}, "seeds": {"WHEAT": 1}, "inventories": [{}]}
    private1 = {"shed": {"WHEAT": 22}, "seeds": {"WHEAT": 2}, "inventories": [{}]}
    private1_next = {
        "shed": {"WHEAT": 22}, "seeds": {"WHEAT": 2}, "inventories": [{}, {}]
    }
    steps = [
        [
            {"observation": observation(0, farms0, private0, 0), "action": {"farmer": ["PASS"], "hands": [], "market": []}, "reward": 0, "status": "ACTIVE"},
            {"observation": observation(1, farms0, private1, 0), "action": {"farmer": ["PASS"], "hands": [], "market": []}, "reward": 0, "status": "ACTIVE"},
        ],
        [
            {"observation": observation(0, farms1, private0, 1, hour=1), "action": {"farmer": ["PASS"], "hands": [], "market": []}, "reward": 100, "status": "DONE"},
            {"observation": observation(1, farms1, private1_next, 1, hour=1), "action": {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}, "reward": 0, "status": "ACTIVE"},
        ],
        [
            {"observation": observation(0, farms1, private0, 2, hour=2), "action": {"farmer": ["PASS"], "hands": [], "market": []}, "reward": 100, "status": "DONE"},
            {"observation": observation(1, farms1, private1_next, 2, hour=2), "action": {"farmer": ["PASS"], "hands": [["NOT_AN_ACTION"]], "market": []}, "reward": 199, "status": "DONE"},
        ],
    ]
    return {
        "id": "fixture", "name": "kaggriculture", "configuration": {
            "episodeSteps": 3, "turnsPerDay": 24, "boardSize": 10,
        }, "info": {"seed": 7}, "steps": steps,
    }


class FakeCohortClient:
    def __init__(self):
        self.rows = [
            {"teamId": 10, "teamName": "Alpha", "score": "1.2500", "submissionDate": "2026-09-10T01:00:00Z"},
            {"teamId": 20, "teamName": "Beta", "score": "1.100", "submissionDate": "2026-09-10T02:00:00Z"},
        ]
        self.submissions = {
            10: [{"id": 101, "dateSubmitted": "2026-09-10T01:00:00Z", "publicScore": "1.25"},
                 {"id": 100, "dateSubmitted": "2026-09-09T01:00:00Z", "publicScore": "1.0"}],
            20: [{"id": 202, "dateSubmitted": "2026-09-10T02:00:00Z", "publicScore": "1.1"}],
        }
        shared = episode(500, "2026-09-10T03:00:00Z", [agent(101, 1, 10, "Alpha", 50), agent(202, 0, 20, "Beta", 60)])
        self.episodes = {101: [shared], 202: [shared]}

    def leaderboard(self, competition, count):
        return self.rows[:count]

    def team_submissions(self, team_id):
        return self.submissions[team_id]

    def submission_episodes(self, submission_id):
        return self.episodes[submission_id]


class FakeDownloadClient:
    def __init__(self, replay=None, fail=False):
        self.replay = replay or small_replay()
        self.fail = fail
        self.calls = 0

    def download_replay(self, episode_id, directory):
        self.calls += 1
        path = directory / f"episode-{episode_id}-replay.json"
        path.write_text("partial")
        if self.fail:
            raise OSError("interrupted")
        path.write_text(json.dumps(self.replay))
        return path


class CohortTests(unittest.TestCase):
    def test_score_matches_decimal_and_leaderboard_date(self):
        row = {"teamId": 1, "score": "1.2300", "submissionDate": "2026-09-10T01:00:00Z"}
        submissions = [
            {"id": 1, "publicScore": "1.23", "dateSubmitted": "2026-09-09T00:00:00Z"},
            {"id": 2, "publicScore": "1.230", "dateSubmitted": "2026-09-10T01:00:00Z"},
        ]
        self.assertEqual(select_scoring_submission(row, submissions)["submission_id"], 2)

    def test_latest_fifteen_and_stable_seat(self):
        episodes = [
            episode(i, f"2026-09-10T{i:02d}:00:00Z", [agent(3, i % 2, 1, "A"), agent(4, 1 - i % 2, 2, "B")])
            for i in range(1, 18)
        ]
        chosen = select_latest_episodes(episodes, 3, 1, 15)
        self.assertEqual([item["id"] for item in chosen], list(range(17, 2, -1)))

    def test_shared_episode_has_two_associations_but_one_file_id(self):
        cohort = capture_cohort(FakeCohortClient(), "kaggriculture", 2, 1, "fixed")
        self.assertEqual(len(cohort["associations"]), 2)
        self.assertEqual({item["episode_id"] for item in cohort["associations"]}, {500})
        seats = {item["team_id"]: item["seat"] for item in cohort["associations"]}
        self.assertEqual(seats, {10: 1, 20: 0})


class ImmutableDownloadTests(unittest.TestCase):
    def test_rerun_does_not_download_again(self):
        client = FakeDownloadClient()
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            first, downloaded = ensure_replay(client, evidence, 1)
            second, downloaded_again = ensure_replay(client, evidence, 1, first)
            self.assertTrue(downloaded)
            self.assertFalse(downloaded_again)
            self.assertEqual(client.calls, 1)
            self.assertEqual(first["sha256"], second["sha256"])

    def test_mismatch_never_replaces_valid_evidence(self):
        client = FakeDownloadClient()
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            path = evidence / "episode-1-replay.json"
            original = json.dumps(small_replay()).encode()
            path.write_bytes(original)
            with self.assertRaises(ValueError):
                ensure_replay(client, evidence, 1, {"sha256": "0" * 64, "byte_size": len(original)})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(client.calls, 0)

    def test_interrupted_download_never_becomes_evidence(self):
        client = FakeDownloadClient(fail=True)
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            with self.assertRaises(OSError):
                ensure_replay(client, evidence, 9)
            self.assertFalse((evidence / "episode-9-replay.json").exists())


class ReplayNormalisationTests(unittest.TestCase):
    def association(self):
        return {
            "association_id": "20:202:500", "episode_id": 500, "rank": 2,
            "team_id": 20, "team_name": "Beta", "leaderboard_score": "1.1",
            "submission_id": 202, "seat": 1, "opponent_team_id": 10,
            "opponent_team_name": "Alpha", "opponent_submission_id": 101,
            "create_time": "start", "end_time": "end", "agents": [
                {"seat": 0, "reward": 100}, {"seat": 1, "reward": 199},
            ],
        }

    def test_720_turn_validation_and_incomplete_rejection(self):
        replay = small_replay()
        replay["configuration"]["episodeSteps"] = 720
        replay["steps"] = [replay["steps"][0] for _ in range(720)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.json"
            path.write_text(json.dumps(replay))
            self.assertEqual(len(load_replay(path)["steps"]), 720)
            replay["steps"].pop()
            path.write_text(json.dumps(replay))
            with self.assertRaises(ReplayValidationError):
                load_replay(path)

    def test_both_perspectives_hired_hand_private_ownership_and_malformed_action(self):
        replay = small_replay()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "evidence" / "episode.json"
            raw.parent.mkdir()
            raw.write_text(json.dumps(replay))
            association = self.association()
            other_association = {
                **association, "association_id": "10:101:500", "rank": 1,
                "team_id": 10, "team_name": "Alpha", "leaderboard_score": "1.25",
                "submission_id": 101, "seat": 0, "opponent_team_id": 20,
                "opponent_team_name": "Beta", "opponent_submission_id": 202,
            }
            manifest = {
                "snapshot_id": "fixture", "cohort": {"associations": [association, other_association]},
                "raw_files": [{
                    "episode_id": 500, "path": "evidence/episode.json", "sha256": sha256_file(raw),
                    "byte_size": raw.stat().st_size, "downloaded_at": "now",
                }],
            }
            counts, tables = normalize_snapshot(manifest, root, root / "raw")
            validate_referential_integrity(tables, manifest)
            self.assertEqual(counts["episodes.parquet"], 2)
            self.assertTrue(any(row["unit_id"] == "hand-0" for row in tables["turns"]))
            hand = next(row for row in tables["turns"] if row["association_id"] == association["association_id"] and row["unit_id"] == "hand-0")
            self.assertTrue(hand["action_malformed"])
            own_turn = next(row for row in tables["turns"] if row["association_id"] == association["association_id"])
            other_turn = next(row for row in tables["turns"] if row["association_id"] == other_association["association_id"])
            self.assertEqual(json.loads(own_turn["shed_json"]), {"WHEAT": 22})
            self.assertEqual(json.loads(other_turn["shed_json"]), {"WHEAT": 11})

            checksums = {name: sha256_file(root / "raw" / name) for name in counts}
            counts_again, tables_again = normalize_snapshot(manifest, root, root / "raw")
            self.assertEqual(counts_again, counts)
            self.assertEqual(
                {name: sha256_file(root / "raw" / name) for name in counts}, checksums
            )
            validate_referential_integrity(tables_again, manifest)
            self.assertEqual(pq.read_table(root / "raw" / "episodes.parquet").num_rows, 2)

    def test_end_of_day_reset_is_not_counted_as_route_movement(self):
        replay = small_replay()
        replay["configuration"].update({"episodeSteps": 2, "turnsPerDay": 1})
        replay["steps"] = replay["steps"][:2]
        replay["steps"][0][1]["observation"]["farms"][1]["farmer"] = [0, 0]
        replay["steps"][1][1]["observation"]["day"] = 1
        replay["steps"][1][1]["observation"]["hour"] = 0
        replay["steps"][1][1]["action"] = {"farmer": ["PASS"], "hands": [], "market": []}
        rows = _turn_rows(replay, self.association(), "fixture")
        farmer = next(row for row in rows if row["step"] == 1 and row["unit_id"] == "farmer")
        self.assertFalse(farmer["moved"])
        self.assertEqual(
            (farmer["position_x"], farmer["position_y"]),
            (farmer["next_position_x"], farmer["next_position_y"]),
        )


class RoutingTests(unittest.TestCase):
    def test_exact_shortest_order_and_precedence(self):
        unconstrained = optimise_route(
            (0, 0), (10, 0), [Waypoint("far", 9, 0), Waypoint("near", 1, 0)]
        )
        self.assertEqual(unconstrained.algorithm, "exact_dp")
        self.assertEqual(unconstrained.order, ("near", "far"))
        self.assertEqual(unconstrained.distance, 10)
        constrained = optimise_route(
            (0, 0), (10, 0), [Waypoint("far", 9, 0, precedes=("near",)), Waypoint("near", 1, 0)]
        )
        self.assertEqual(constrained.order, ("far", "near"))
        self.assertEqual(constrained.distance, 26)

    def test_shed_waypoint_deadline_and_approximate_label(self):
        route = optimise_route(
            (0, 0), (0, 0),
            [Waypoint("shed", 4, 4, "acquire", precedes=("field",)), Waypoint("field", 9, 9)],
            deadline_steps=5,
        )
        self.assertEqual(route.order[0], "shed")
        self.assertFalse(route.feasible)
        many = optimise_route((0, 0), (0, 0), [Waypoint(str(i), i % 10, i // 10) for i in range(13)])
        self.assertEqual(many.algorithm, "insertion_2opt")

    def test_route_score_uses_shadow_over_actual(self):
        base = {
            "snapshot_id": "s", "association_id": "a", "episode_id": 1, "team_id": 2,
            "seat": 0, "day": 0, "unit_id": "farmer", "action_args_json": "[]",
            "action_json": '["EAST"]', "inventory_json": "{}", "at_shed": False,
            "inferred_noop": False,
        }
        rows = []
        positions = [((0, 0), (0, 1)), ((0, 1), (1, 1)), ((1, 1), (1, 0))]
        for step, (start, end) in enumerate(positions):
            rows.append({
                **base, "step": step, "hour": step, "position_x": start[0], "position_y": start[1],
                "next_position_x": end[0], "next_position_y": end[1], "action_op": "EAST",
            })
        row = _route_row(rows, 0, 24)
        self.assertEqual(row["actual_movement"], 3)
        self.assertEqual(row["shadow_movement"], 1)
        self.assertAlmostEqual(row["route_score"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
