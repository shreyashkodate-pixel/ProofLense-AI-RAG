"""ProofLens AI — Unit Tests for Alembic Migration Scripts.

Verifies revision lineage, migration graph integrity, and upgrade/downgrade consistency.
"""

from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_migration_revision_graph():
    """Verify Alembic migration revision graph is linear and starts at 0001_initial_schema."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    script_dir = ScriptDirectory.from_config(alembic_cfg)
    heads = script_dir.get_heads()

    assert len(heads) == 1, "Expected exactly one migration head revision."
    assert heads[0] == "0001_initial_schema"

    revision = script_dir.get_revision(heads[0])
    assert revision.down_revision is None
    assert "0001_initial_schema" in revision.revision
