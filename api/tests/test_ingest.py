"""Ingest safety. SPECIFICATIONS.MD 5.1.

No network here: the fetch is exercised against fixed rows, because a test that
depends on wger.de being up is a test that fails for reasons unrelated to this
code.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domain.models import Exercise
from app.ingest.mapping import MappingReport, map_equipment, map_muscle, validate_canonical
from app.ingest.wger import Staged, _to_steps, load


def a_row(**overrides) -> dict:
    return {
        "source": "wger", "source_id": "9001", "source_version": "v1",
        "name": "Sledgehammer Swing", "name_normalized": "sledgehammer swing",
        "aliases": [], "body_part": "core", "primary_muscle": "obliques",
        "secondary_muscles": ["lats"], "equipment": ["bodyweight"],
        "difficulty": "intermediate", "type": "compound",
        "metric_type": "bodyweight_reps", "bodyweight_load_factor": "0.65",
        "default_rest_seconds": 120, "instructions": ["Swing it."],
        "image_url": None, "gif_url": None, "video_url": None,
        "media_licence": None, **overrides,
    }


class TestMapping:
    def test_unmapped_values_are_reported_never_dropped(self):
        """Sec 4 - an unmapped value is a data error surfaced in a report."""
        report = MappingReport()
        assert map_equipment("Moon Boots") is None
        report.note_equipment("Moon Boots")
        assert not report.clean
        assert "Moon Boots" in report.summary()

    def test_known_synonyms_map(self):
        assert map_equipment("Cable machine") == "cable"
        assert map_muscle("Quads") == "quads"

    def test_validation_catches_a_bad_row(self):
        problems = validate_canonical(
            body_part="elbow", primary="gills", secondary=["fins"], equipment=[]
        )
        assert len(problems) == 4

    def test_html_descriptions_become_plain_steps(self):
        steps = _to_steps("<p>Stand up straight.</p><ul><li>Brace your core hard</li></ul>")
        assert steps == ["Stand up straight.", "Brace your core hard"]

    def test_short_fragments_are_dropped(self):
        assert _to_steps("<p>Go.</p>") == []


class TestLoad:
    def test_an_empty_fetch_never_replaces_the_catalogue(self, db):
        """Sec 5.1 - a failed or partial ingest never replaces a good dataset."""
        before = db.execute(select(Exercise)).scalars().all()
        with pytest.raises(RuntimeError):
            load(db, Staged(rows=[]))
        assert len(db.execute(select(Exercise)).scalars().all()) == len(before)

    def test_a_new_row_is_created_and_re_running_updates_it(self, db):
        load(db, Staged(rows=[a_row()]), attach_media_to_seed=False)
        found = db.execute(
            select(Exercise).where(Exercise.source_id == "9001")
        ).scalar_one()
        assert found.name == "Sledgehammer Swing"
        original_id = found.id

        load(db, Staged(rows=[a_row(name="Sledgehammer Swing v2")]),
             attach_media_to_seed=False)
        again = db.execute(
            select(Exercise).where(Exercise.source_id == "9001")
        ).scalar_one()
        # The id must survive, or every logged set pointing at it is orphaned.
        assert again.id == original_id
        assert again.name == "Sledgehammer Swing v2"

    def test_an_import_never_shadows_a_hand_written_seed_entry(self, db):
        """The seed rows carry correct metric types; an import must not
        overwrite a movement we already describe properly."""
        load(
            db,
            Staged(rows=[a_row(source_id="9002", name="Barbell Row",
                               name_normalized="barbell row")]),
            attach_media_to_seed=False,
        )
        rows = db.execute(
            select(Exercise).where(Exercise.name_normalized == "barbell row")
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].source == "custom"

    def test_media_is_attached_to_matching_seed_rows(self, db):
        load(
            db,
            Staged(rows=[a_row(source_id="9003", name="Barbell Row",
                               name_normalized="barbell row",
                               image_url="https://example.test/row.png")]),
        )
        seed = db.execute(
            select(Exercise).where(Exercise.name_normalized == "barbell row")
        ).scalar_one()
        assert seed.image_url == "https://example.test/row.png"
        assert seed.media_licence is not None

    def test_the_run_is_recorded(self, db):
        from app.domain.models import IngestRun

        load(db, Staged(rows=[a_row()]), attach_media_to_seed=False)
        run = db.execute(
            select(IngestRun).where(IngestRun.source == "wger")
        ).scalars().first()
        assert run is not None
        assert run.status == "succeeded"
        assert run.rows_written == 1
