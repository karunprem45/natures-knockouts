"""Artifacts: the unit every agent posts. Mirrors the organizers' artifact layer:
UUID, content hash, parent lineage, needs broadcast. Stored append-only as JSONL."""
import hashlib, json, threading, uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

TYPES = {"evidence", "fulfillment", "challenge", "revision", "error"}


@dataclass
class Artifact:
    artifact_type: str
    producer_agent: str
    gene_code: str
    round: int
    stance: str = "neutral"
    strength: float = 0.0
    rationale: str = ""
    data_refs: list = field(default_factory=list)
    parent_artifact_ids: list = field(default_factory=list)
    needs: list = field(default_factory=list)
    challenges: list = field(default_factory=list)   # skeptic only
    error: str | None = None
    flags: list = field(default_factory=list)        # e.g. "identity_named:<n>" when output was redacted
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_hash: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        assert self.artifact_type in TYPES, self.artifact_type
        if not self.content_hash:
            body = {k: v for k, v in asdict(self).items()
                    if k not in ("artifact_id", "content_hash", "timestamp")}
            self.content_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    def add_flag(self, flag):
        """Add a flag and recompute the content hash so provenance stays exact."""
        self.flags.append(flag)
        self.content_hash = ""
        self.__post_init__()
        return self

    def to_json(self):
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class ArtifactStore:
    """Append-only JSONL file shared by every agent in a run."""

    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, artifact):
        with self._lock, self.path.open("a") as f:
            f.write(artifact.to_json() + "\n")
        return artifact

    def all(self, gene_code=None):
        if not self.path.exists():
            return []
        arts = [Artifact.from_dict(json.loads(l)) for l in self.path.read_text().splitlines() if l.strip()]
        return [a for a in arts if gene_code is None or a.gene_code == gene_code]
