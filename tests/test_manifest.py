import json

from vball import manifest


def setup(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    (models / "a.onnx").write_bytes(b"weights a")
    (models / "b.pt").write_bytes(b"weights b")
    m = models / "manifest.json"
    m.write_text(
        json.dumps(
            {
                "a.onnx": {
                    "sha256": manifest.sha256(models / "a.onnx"),
                    "bytes": 9,
                    "source": "upstream",
                    "measured_in": None,
                },
                "b.pt": {"sha256": "0" * 64, "bytes": 1, "source": "trained here", "measured_in": "docs/results/x.md"},
                "c.pt": {"sha256": "0" * 64, "bytes": 1, "source": "trained here", "measured_in": None},
            }
        )
    )
    return models, m


def test_check_reports_missing_and_changed_files(tmp_path):
    models, m = setup(tmp_path)
    assert manifest.check(models, m) == {"b.pt": "changed", "c.pt": "missing"}


def test_usable_needs_the_listed_checksum_inside_models_only(tmp_path):
    models, m = setup(tmp_path)
    assert manifest.usable(models / "a.onnx", models, m)
    assert not manifest.usable(models / "b.pt", models, m)  # changed
    assert not manifest.usable(models / "c.pt", models, m)  # missing
    fake = tmp_path / "fake.pt"
    fake.write_bytes(b"")
    assert manifest.usable(fake, models, m)  # outside models/: existence is enough
    (models / "new.pt").write_bytes(b"x")
    assert manifest.usable(models / "new.pt", models, m)  # not listed yet


def test_write_updates_checksums_and_keeps_metadata(tmp_path):
    models, m = setup(tmp_path)
    entries = manifest.write(models, m)
    assert entries["b.pt"]["sha256"] == manifest.sha256(models / "b.pt") and entries["b.pt"]["bytes"] == 9
    assert entries["b.pt"]["measured_in"] == "docs/results/x.md"
    assert entries["c.pt"]["sha256"] == "0" * 64  # missing files keep their entry
    assert manifest.check(models, m) == {"c.pt": "missing"}
    assert manifest.load(tmp_path / "none.json") == {}
    assert manifest.external_source({"external": "repo/x.onnx"}).name == "x.onnx"
    assert manifest.external_source({}) is None


def test_fetch_copies_from_external_and_checks_the_checksum(tmp_path, monkeypatch):
    models, m = setup(tmp_path)
    upstream = tmp_path / "external" / "repo"
    upstream.mkdir(parents=True)
    (upstream / "c.pt").write_bytes(b"upstream c")
    monkeypatch.setattr(manifest, "EXTERNAL", tmp_path / "external")
    good = {"sha256": manifest.sha256(upstream / "c.pt"), "source": "upstream", "external": "repo/c.pt"}
    assert manifest.fetch("c.pt", good, models) == "fetched" and (models / "c.pt").exists()
    (models / "c.pt").unlink()
    bad = {**good, "sha256": "0" * 64}
    assert manifest.fetch("c.pt", bad, models) == "fetched, but the checksum differs: removed"
    assert not (models / "c.pt").exists()
    assert (
        manifest.fetch("c.pt", {"sha256": "0" * 64, "source": "notebooks/x.ipynb"}, models)
        == "not fetchable: notebooks/x.ipynb"
    )
