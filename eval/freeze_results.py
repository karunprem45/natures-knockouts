"""R7: copy every arm's outputs into frozen_results/ with SHA-256 hashes, so results are fixed.

Run once after the arms finish (before evaluation) and again after the report; the git history
shows the raw scores were committed before any metric was computed.
"""
import hashlib, shutil
import config

OUT = config.ROOT / "frozen_results"
KEEP = ["scores.csv", "board.jsonl", "meta.json", "llm_log.jsonl", "imputation_log.md"]


def main():
    arms = sorted(p for p in config.RUNS_DIR.iterdir() if p.is_dir() and (p / "scores.csv").exists())
    for arm in arms:
        dest = OUT / "runs" / arm.name
        dest.mkdir(parents=True, exist_ok=True)
        for name in KEEP:
            if (arm / name).exists():
                shutil.copy2(arm / name, dest / name)
    for extra in ["RERUN_LOG.md", "baselines_table.md"]:
        if (config.RUNS_DIR / extra).exists():
            shutil.copy2(config.RUNS_DIR / extra, OUT / extra)
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}" for p in files]
    (OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(f"froze {len(arms)} arms, {len(files)} files -> {OUT}/SHA256SUMS")


if __name__ == "__main__":
    main()
