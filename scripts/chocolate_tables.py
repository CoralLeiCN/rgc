"""Table operations without coercing original chocolate source records.

Compatibility builders select the standard-library backend by default. The
combined silver builder selects pandas explicitly; imports remain lazy so the
standalone helpers do not acquire a pandas dependency.
"""

import importlib
import platform
from collections import Counter, defaultdict

ROLES = ("brand", "retail", "unknown")


class TableBackend:
    """Group derived metadata while retaining original row objects and order."""

    def __init__(self, name):
        if name not in ("stdlib", "pandas"):
            raise ValueError("Unknown chocolate table backend: " + str(name))
        self.name = name
        self.pd = None
        if name == "pandas":
            try:
                self.pd = importlib.import_module("pandas")
            except ImportError as error:
                raise RuntimeError(
                    "The chocolate silver pandas backend requires pandas. "
                    "Use uv run scripts/build_chocolate_silver.py or install pandas==2.2.3 "
                    "in the Python environment running the build."
                ) from error

    def runtime(self):
        result = {"table_backend": self.name,
                  "python_implementation": platform.python_implementation(),
                  "python_version": platform.python_version()}
        if self.pd is not None:
            result["pandas_version"] = self.pd.__version__
            result["numpy_version"] = importlib.import_module("numpy").__version__
        return result

    def frame(self, columns):
        """Use object columns; source numbers, strings, nulls and lists stay exact."""
        return self.pd.DataFrame(columns, dtype=object)

    def identity_groups(self, identities):
        """Group precise seller keys, isolating every unresolved listing ID.

        Keys were already validated by source_identity. In particular, a null
        variant is a valid identity component and must not disappear in groupby.
        """
        if self.pd is None:
            grouped = defaultdict(list)
            for listing, key in identities:
                grouped[key if key is not None else ("unresolved", listing)].append(listing)
            return [sorted(ids) for ids in grouped.values()]
        columns = {name: [] for name in
                   ("listing_id", "source_key", "hostname", "product_id", "variant_id", "unresolved_listing")}
        for listing, key in identities:
            columns["listing_id"].append(listing)
            for name, value in zip(("source_key", "hostname", "product_id", "variant_id"),
                                   key if key is not None else (None, None, None, None)):
                columns[name].append(value)
            columns["unresolved_listing"].append(listing if key is None else None)
        if not columns["listing_id"]:
            return []
        frame = self.frame(columns)
        keys = [name for name in columns if name != "listing_id"]
        groups = frame.groupby(keys, sort=False, dropna=False)["listing_id"].agg(list)
        return [sorted(ids) for ids in groups.tolist()]

    def counts(self, rows, column):
        if self.pd is None:
            return dict(Counter(row[column] for row in rows))
        frame = self.frame({column: [row[column] for row in rows]})
        return {key: int(count) for key, count in
                frame.groupby(column, sort=False, dropna=False).size().items()}

    def attribute_counts(self, products):
        """Count known/conflicting derived states without flattening source values."""
        if self.pd is None:
            return tuple(dict(Counter(name for row in products for name, attribute in row["attributes"].items()
                                      if attribute["status"] == state)) for state in ("known", "conflict"))
        attributes, states = [], []
        for row in products:
            for name, attribute in row["attributes"].items():
                attributes.append(name)
                states.append(attribute["status"])
        frame = self.frame({"attribute": attributes, "status": states})
        counts = frame.groupby(["status", "attribute"], sort=False, dropna=False).size()
        return tuple({name: int(count) for (status, name), count in counts.items() if status == state}
                     for state in ("known", "conflict"))

    def exclusion_counts(self, candidates):
        if self.pd is None:
            return dict(Counter(reason for row in candidates for reason in row["exclusion_reasons"]))
        frame = self.frame({"reason": [row["exclusion_reasons"] for row in candidates]})
        # An empty exclusion list means eligibility, never an unknown reason.
        reasons = frame.explode("reason").dropna(subset=["reason"])
        return {reason: int(count) for reason, count in
                reasons.groupby("reason", sort=False, dropna=False).size().items()}

    def select(self, rows, column, value):
        if self.pd is None:
            return [row for row in rows if row[column] == value]
        frame = self.frame({"position": list(range(len(rows))),
                            column: [row[column] for row in rows]})
        return [rows[position] for position in frame.loc[frame[column] == value, "position"].tolist()]

    def partitions(self, rows):
        """Return stable source-role partitions, keeping original row references."""
        if self.pd is None:
            return {role: [row for row in rows if row["source_role"] == role] for role in ROLES}
        frame = self.frame({"position": list(range(len(rows))),
                            "source_role": [row["source_role"] for row in rows]})
        grouped = {role: positions.tolist() for role, positions in
                   frame.groupby("source_role", sort=False, dropna=False)["position"]}
        return {role: [rows[position] for position in grouped.get(role, [])] for role in ROLES}

    def envelopes(self, rows, version, source_version, layer_version):
        """Replace only derived top-level envelopes; nested evidence is opaque."""
        if self.pd is None:
            for original in rows:
                row = dict(original)
                row.update(dataset_version=version, source_dataset_version=source_version)
                if "layer_version" in row:
                    row["layer_version"] = layer_version
                yield row
            return
        frame = self.frame({"original": rows,
                            "has_layer": ["layer_version" in row for row in rows]})
        frame = frame.assign(dataset_version=version, source_dataset_version=source_version)
        for original, has_layer, dataset, source in frame.itertuples(index=False, name=None):
            row = dict(original)
            row.update(dataset_version=dataset, source_dataset_version=source)
            if has_layer:
                row["layer_version"] = layer_version
            yield row


def get_table_backend(backend="stdlib"):
    return backend if isinstance(backend, TableBackend) else TableBackend(backend)
