# Dataset-owned analytical contracts

The authoritative analytical contracts live in the
[CoralLeiCN/rgc-collections Hugging Face dataset](https://huggingface.co/datasets/CoralLeiCN/rgc-collections).
Human documentation and small version references remain in Git. Runtime caches
and generated snapshot copies do not replace the authoritative dataset files.
The dataset also contains the raw text-evidence export and published silver
snapshots. A published silver snapshot is not necessarily reviewed or
model-ready; this storage migration does not rebuild local silver.

| Contract set | Dataset path | Git reference |
| --- | --- | --- |
| Established chocolate schema | `contracts/chocolate/` | [Chocolate manifest](../../schemas/chocolate/dataset-contract.json) |
| Portable chocolate processing | `contracts/category-processing/chocolate/` | [Portable chocolate manifest](../../plugins/category-processing/profiles/chocolate/dataset-contract.json) |
| Portable coffee starter | `contracts/category-processing/coffee/` | [Portable coffee manifest](../../plugins/category-processing/profiles/coffee/dataset-contract.json) |

Each set contains `profile.json`, `source-mappings.json`, `product.schema.json`
and `model-design.json`; portable sets also contain `pipeline.json`.
Manifests use `rgc-dataset-contract-reference-1` and record the repository ID,
immutable 40-character dataset commit, contract set, category/market, existing
semantic versions, attribute count, and each file's dataset path, SHA-256 and
byte length. No `main` or other moving revision is accepted by the loader.

## Fetch, cache and offline use

Populate all default caches before offline processing or semantic test runs:

```sh
python3 -B scripts/fetch_contracts.py --all
python3 -B scripts/fetch_contracts.py --all --offline
```

The established chocolate cache is under `data/contract-cache/`; the portable
package uses `plugins/category-processing/.contract-cache/`. Below each root,
files are partitioned by repository, immutable revision and contract set. A
cache marker preserves the exact dataset reference. `--cache-root <directory>`
can populate an explicitly supplied root; consumers must use that same root.
These cache payloads are ignored by Git.

Loaders verify every available file's byte length and SHA-256 before reuse and
reject mismatched cache metadata or corrupt bytes. On a cache miss, online
resolution downloads only the pinned files; offline resolution fails with a
clear missing-cache error. It never substitutes the latest dataset revision.
Silver/model-preparation snapshots retain exact contract copies and provenance
so an older result remains reproducible after a newer dataset revision exists.

The portable CLI accepts `--category chocolate` or `--category coffee`,
`--contracts-cache <directory>` and `--offline`; explicit `--profile` directories
remain supported for custom profiles and compatibility.

## Maintenance and verification

Edit a local working copy, preserve source evidence, bump affected semantic
versions when meanings change, and validate the aligned contracts. Publish them
after the [completed schema release review](../decisions/agent-led-schema-maintenance.md#review-before-a-hugging-face-commit)
to a new dataset commit, verify the published bytes, then update the Git
manifest pins/hashes and corresponding documentation. A storage-only migration
preserves contract bytes and existing schema/mapping/model/recipe versions.
Keep generated snapshot copies immutable; rebuild under the new reference
instead of changing an old result.

`scripts/publish_contracts.py` accepts a prepared source tree containing the
three `contracts/<contract-set>/` directories above. It publishes only their
14 JSON files, `contracts/manifest.json` and the analytical-contract section of
the dataset card. It preserves existing raw export and silver files. Publication
uses Python 3.10 or later and the script's pinned `huggingface_hub` dependency:

```sh
uv run scripts/publish_contracts.py \
  --source-root /path/to/prepared-contracts \
  --upload --write-references \
  --receipt data/contract-publication-receipt.json
```

The publisher verifies remote bytes before updating local reference manifests;
the receipt records the resulting commit and managed files. Omit `--upload` to
inspect the prepared inventory. Contract publication is separate from the raw
text-evidence exporter and does not authorize a new evidence or silver rebuild.

```sh
uv sync --locked
uv run ruff check .
python3 -B scripts/check_documentation.py
uv run pytest scripts/tests/test_dataset_contracts.py scripts/tests/test_documentation.py
```

The documentation guard works offline in a clean clone. It checks manifest
format/pins, expected file sets and documented versions without downloading
schemas. If default caches exist, it also verifies available bytes; it checks
cross-file schema/catalog consistency when a complete set is available. A
partial cache is not a missing repository source file. Remote existence and
successful publication require separate verification; a passing offline guard
does not establish either.

The current executable preparation contracts remain distinct from the
[proposed pricing research design](chocolate-modeling-design.md). Moving storage
does not implement LightGBM, optional-feature imputation, calibrated prediction
intervals or a new model contract.

## Model artifacts

Published model artifacts use `model/` in the same dataset. Follow the
[model maintenance guide](../model-maintenance.md) for immutable run directories,
Git references, remote byte verification and retraining. Generated model files
stay outside Git; analytical contract ownership and release review still apply.

## Current contract release

On 2026-10-03, the user-approved Gold/modeling release was published at immutable commit `d549ad91d63fb452af605df4a939c4e1f0a59bfa`. All 16 managed files were downloaded and verified byte for byte; the three Git references now pin that revision. The release preserves the intervening published Silver and analysis files. [The release record](analysis/gold-modeling-contract-release.md) lists exact hashes, versions and corpus impact. Existing snapshots retain their copied historical contracts.


The current chocolate modeling study adds a separate `chocolate-current-price`
contract set with four files, using the standard immutable reference/cache
format. Its profile, mappings and validator match the historical chocolate
contract bytes; `model-design.json` specifies
`chocolate-pricing-current-price-design-1` and `current-consumer-price-1`.
`fetch_contracts.py --all` includes its pin when present, and the documentation
guard validates the pin offline and every available cached file. Historical
source and portable processing contract sets retain their own price basis.

The current-price contract was published at immutable revision
`d743cb8dbca37f5241cccd444a16165523304f6c`. Its five uploaded files were
downloaded and verified byte for byte. The new pin is
[the current-price reference](../../schemas/chocolate/current-price/dataset-contract.json).
The four contract bodies occupy `contracts/chocolate-current-price/`; the
existing index gains this contract set. The source and portable contract pins
retain their historical revisions.

The Gold publication at `95c5fbd0ab5fa9a41fa5333648321d95f16927a7` adds the
immutable all-eligible snapshot and its latest pointer. The
[Gold data reference](../../schemas/chocolate/gold-dataset.json) records the
manifest and each managed file checksum. All 25 uploaded files were downloaded,
compared byte for byte and loaded with the verified Gold interface. The
[Gold guide](chocolate-gold.md#published-all-eligible-training-snapshot) describes
its exact path and current-price trainer handoff.

The independent [hedonic implementation](analysis/hedonic-without-brand-implementation.md) materializes an explicit unpublished working experiment policy in an ignored directory. Its new analytical handoff is not supplied by the published producer contracts. Original and portable pins remain unchanged; a future supported producer migration must synchronize all affected contracts and pass the established release review before a Hugging Face contract commit.
