import csv
import io

import pytest

from test_api import upload


@pytest.fixture
def match(client, clip):
    """Two rallies in set 1: A wins 0-10 s, B wins 12-20 s."""
    import main
    v = upload(client, clip)
    main.db.replace_rallies(v["id"], [
        {"idx": 0, "start_s": 0, "end_s": 10, "winner": "a", "source": "model"},
        {"idx": 1, "start_s": 12, "end_s": 20, "winner": "b", "source": "model"},
    ])
    return v["id"]


def tag(client, vid, **body):
    r = client.post(f"/videos/{vid}/tags", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_roster_rejects_a_duplicate_number_and_keeps_the_old_roster(client, match):
    ok = {"players": [{"team": "a", "number": 7, "name": "Lin"}, {"team": "b", "number": 7}]}
    assert client.put(f"/videos/{match}/roster", json=ok).status_code == 200
    dup = {"players": [{"team": "a", "number": 7}, {"team": "a", "number": 7}]}
    r = client.put(f"/videos/{match}/roster", json=dup)
    assert r.status_code == 400 and "listed twice for team A" in r.json()["detail"]
    assert client.get(f"/videos/{match}/roster").json()["players"] == [
        {"team": "a", "number": 7, "name": "Lin"}, {"team": "b", "number": 7, "name": None}]


def test_tagging_an_unknown_number_adds_it_to_the_roster(client, match):
    tag(client, match, time_s=15, kind="attack", team="b", number=12)
    assert {"team": "b", "number": 12, "name": None} in client.get(f"/videos/{match}/roster").json()["players"]


def test_outcomes_follow_the_winner_and_its_correction(client, match):
    tags = tag(client, match, time_s=8, kind="attack", team="a", number=10)
    assert (tags[0]["effective_outcome"], tags[0]["inferred"], tags[0]["rally_idx"]) == ("kill", True, 0)
    client.patch(f"/videos/{match}/rallies/0", json={"winner": "b"})
    t = client.get(f"/videos/{match}/tags").json()[0]
    assert t["effective_outcome"] == "error"
    line = [x for x in client.get(f"/videos/{match}/stats").json()["lines"]
            if x["number"] == 10 and x["set_no"] is None][0]
    assert (line["attempts"], line["attack_errors"], line["efficiency"]) == (1, 1, -1.0)


def test_patch_sets_and_clears_the_user_outcome_and_delete_removes(client, match):
    tid = tag(client, match, time_s=8, kind="attack", team="a", number=10)[0]["id"]
    t = client.patch(f"/videos/{match}/tags/{tid}", json={"outcome": "in_play"}).json()[0]
    assert (t["outcome"], t["effective_outcome"], t["inferred"]) == ("in_play", "in_play", False)
    t = client.patch(f"/videos/{match}/tags/{tid}", json={"outcome": None}).json()[0]
    assert (t["outcome"], t["effective_outcome"]) == (None, "kill")
    assert client.patch(f"/videos/{match}/tags/{tid}", json={"outcome": "ace"}).status_code == 400
    assert client.delete(f"/videos/{match}/tags/{tid}").json() == []
    assert client.delete(f"/videos/{match}/tags/{tid}").status_code == 404


def test_invalid_tag_is_rejected(client, match):
    r = client.post(f"/videos/{match}/tags", json={"time_s": 1, "kind": "serve", "team": "a", "number": 7,
                                                   "outcome": "kill"})
    assert r.status_code in (400, 422)


def test_tags_survive_reanalysis_that_moves_rally_boundaries(client, match):
    import main
    tag(client, match, time_s=11, kind="attack", team="b", number=4)
    assert client.get(f"/videos/{match}/tags").json()[0]["rally_idx"] == 0  # 1 s after rally 0
    main.db.replace_rallies(match, [  # re-analysis: rally 1 now starts at 10.8 s
        {"idx": 0, "start_s": 0, "end_s": 10.5, "winner": "a", "source": "model"},
        {"idx": 1, "start_s": 10.8, "end_s": 20, "winner": "b", "source": "model"},
    ])
    t = client.get(f"/videos/{match}/tags").json()
    assert len(t) == 1 and t[0]["rally_idx"] == 1 and t[0]["effective_outcome"] == "kill"


def test_stats_json_and_csv(client, match):
    client.put(f"/videos/{match}/roster", json={"players": [{"team": "a", "number": 10, "name": "Wu"}]})
    tag(client, match, time_s=1, kind="serve", team="a", number=7)
    tag(client, match, time_s=8, kind="attack", team="a", number=10)
    tag(client, match, time_s=30, kind="attack", team="a", number=10)  # outside any rally
    s = client.get(f"/videos/{match}/stats").json()
    assert (s["rallies"], s["tagged_rallies"], s["outside"]) == (2, 1, 1)
    wu = [x for x in s["lines"] if x["number"] == 10 and x["set_no"] is None][0]
    assert (wu["name"], wu["attempts"], wu["kills"], wu["kill_rate"]) == ("Wu", 1, 1, 1.0)

    r = client.get(f"/videos/{match}/stats", params={"format": "csv"})
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="match-stats.csv"' in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0][:4] == ["team", "number", "name", "set"]
    assert ["A", "10", "Wu", "match"] == rows[[i for i, x in enumerate(rows) if x[1] == "10" and x[3] == "match"][0]][:4]


def test_stats_endpoints_404_for_unknown_video(client):
    for path in ("roster", "tags", "stats"):
        assert client.get(f"/videos/nope/{path}").status_code == 404
