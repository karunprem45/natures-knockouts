# Substitutions against BUILD.md (Open Targets release 26.09)

BUILD.md §1a: "If a field named in this doc does not exist, substitute the closest real one and log the substitution."

| BUILD.md says | Reality in OT 26.09 | What the code does |
| --- | --- | --- |
| ChEMBL evidence (`chembl` datasource) | Drug evidence is served as datasource **`clinical_precedence`** (`datatypeId: clinical`, carries `clinicalStage`) | `config.LABEL_DATASOURCES = ["clinical_precedence", "chembl"]`; these rows are written only to `data/labels/chembl/` |
| LOEUF / pLI | `Target.geneticConstraint[constraintType="lof"]`: `oeUpper` = LOEUF, `score` = pLI | `tolerance_view` |
| DepMap essentiality | `Target.depMapEssentiality[].screens[].geneEffect` and `Target.isEssential` | mean gene effect, fraction of screens < -0.5, core-essential flag |
| GWAS rows | datasource `gwas_credible_sets`; direction, beta and p sit on `credibleSet`, not on the evidence row; `directionOnTrait` is null | GWAS view reports `beta` and lead-variant consequence; no direction field |
| `fetch_pool` with `enableIndirect: true` | `Target.evidences` takes exact disease ids only; `Disease.evidences` / `Disease.associatedTargets` support `enableIndirect` | Pool uses `Disease.*` over `config.POOL_SEED_DISEASES`; per-gene pull uses `Target.associatedDiseases(includeMeasurements: true)` to get disease ids first |
| Trait scope `"ischaemic heart"`, `"ALT"`, `"AST"` | OT spells "ischemic" and names the enzymes "alanine/aspartate aminotransferase" | Added `"ischemic heart"`, `"ischemic"`, `"aminotransferase"` to `config.py`; short terms (≤5 chars) match on word boundaries so "AST" does not match "waist" |
| Some BRaVa burden rows | `directionOnTrait` is null | Kept in the views with `direction_on_trait: null`; not counted as protective in the pool |

## Known caveat (put on the limitations slide)

For quantitative traits OT assigns `directionOnTrait` from the sign of beta, so a LoF that *lowers HDL* may be labelled "protect". The Burden agent sees `beta` and the trait name and can reason about it; the pool filter cannot.
