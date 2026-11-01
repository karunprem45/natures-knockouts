"""P2-1 step 4: one A3 run on panel 2 with the unchanged agents, loop and skeptic (seed 1).

  python -m exploratory.v2.run_v2 [--limit N]

Points the agents at data/views_v2 and runs arms.run_arm unchanged; outputs to exploratory/v2/runs/A3_v2_s1.
"""
import sys
import config


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    config.VIEWS_DIR = config.DATA_DIR / "views_v2"
    from arms import run_arm
    out = "exploratory/v2/runs/A3_v2_s1" + ("_smoke" if "--limit" in argv else "")
    run_arm.main(["--arm", "A3", "--seed", "1", "--panel", "exploratory/v2/panel2.csv", "--out", out,
                  "--workers", "5", *argv])


if __name__ == "__main__":
    main()
