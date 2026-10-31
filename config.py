"""Constants only, no logic. Everything here is frozen at the `prereg` tag (R6)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- Paths -----------------------------------------------------------------
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
LABELS_DIR = DATA_DIR / "labels"          # R3: no agent ever reads this
CHEMBL_DIR = LABELS_DIR / "chembl"
VIEWS_DIR = DATA_DIR / "views"            # R2: views/<agent>/<Gene_NN>.json
FROZEN_DIR = ROOT / "frozen"
RUNS_DIR = ROOT / "runs"
PROBE_RESULTS = ROOT / "probes" / "results"

# --- Determinism (R9) ------------------------------------------------------
SEED = 20261031
TEMPERATURE = 0.0

# --- LLM (R1: same model, same cap, every arm) -----------------------------
LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
LLM_MODEL = "gemini-2.5-flash"
MAX_LLM_CALLS_PER_GENE = 10
LLM_MAX_ATTEMPTS = 4
LLM_WORKERS = 10

# --- External services -----------------------------------------------------
OT_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
ENSEMBL_REST_URL = "https://rest.ensembl.org"
ENSEMBL_SLEEP_S = 0.1
EVO2_URLS = [
    "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/forward",
    "https://health.api.nvidia.com/v1/biology/arc/evo2-7b/forward",
]
EVO2_LAYER_NAMES = ["output_layer", "unembed"]
EVO2_WINDOW_BP = 4096
RAW_CACHE_TTL_H = 24

# --- Trait scope (never change after freeze) -------------------------------
TRAIT_SCOPE = {
    "lipids":    ["LDL", "HDL", "triglyceride", "cholesterol", "lipoprotein"],
    "cardio":    ["coronary", "myocardial", "ischaemic heart", "atherosclero"],
    "metabolic": ["type 2 diabetes", "body mass index", "obesity", "waist", "fat distribution"],
    "liver":     ["liver", "hepatic", "ALT", "AST", "steatosis", "cirrhosis", "NAFLD"],
}
HARD_ENDPOINT_TERMS = ["coronary", "myocardial", "diabetes", "cirrhosis", "ischaemic"]

# --- Panel -----------------------------------------------------------------
POSITIVES = ["PCSK9", "ANGPTL3", "APOC3", "ANGPTL4", "NPC1L1", "ASGR1",
             "SLC30A8", "MAP3K15", "HSD17B13", "CIDEB", "GPR75", "INHBE"]
N_POSITIVES = 12
N_NEGATIVES = 28
# Fallback if the 6:30 PM gate fails
N_POSITIVES_FALLBACK = 8
N_NEGATIVES_FALLBACK = 16

# --- Agents ----------------------------------------------------------------
EVIDENCE_AGENTS = ["burden", "gwas", "tolerance", "safety", "variant"]
ALL_AGENTS = EVIDENCE_AGENTS + ["skeptic"]
SKEPTIC_CHALLENGES = ["underpowered", "single_cohort", "single_ancestry",
                      "biomarker_only", "direction_conflict", "essential_gene"]

# --- Board pressure (organizers' published formula, verbatim) --------------
PRESSURE_W_NOVELTY = 2.0
PRESSURE_W_CENTRALITY = 1.0
PRESSURE_W_DEPTH = 0.5
PRESSURE_W_AGE = 0.2

# --- Scoring (R5: Python only) ---------------------------------------------
CHANNEL_WEIGHTS = {a: 1.0 for a in EVIDENCE_AGENTS}
STANCE_VALUE = {"supports": 1.0, "neutral": 0.0, "against": -1.0}
SKEPTIC_DISCOUNT = 0.5

# --- Evaluation ------------------------------------------------------------
N_BOOTSTRAP = 1000
N_PERMUTATIONS = 1000
PRECISION_AT_K = 12
N_SEEDS = 2
