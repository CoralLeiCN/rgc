"""Coverage and value distributions for effective Silver facts, without a model."""

import math
from collections import Counter, defaultdict

from .archive import digest
from .silver_contracts import STATES, column, result_state
from .source_index import encoded


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    point = (len(ordered) - 1) * fraction
    low, high = math.floor(point), math.ceil(point)
    return ordered[low] + (ordered[high] - ordered[low]) * (point - low)


def statistics(facts, definition, backend="python"):
    n = len(facts)
    states = Counter(result_state(item["result"]) for item in facts)
    methods = Counter(item["method"] or "none" for item in facts)
    cross = Counter((item["method"] or "none", result_state(item["result"])) for item in facts)
    available = [item for item in facts if result_state(item["result"]) == "available"]
    k = len(available)
    report = {"N": n, "K": k, "coverage": k / n if n else None,
              "states": {state: states[state] for state in ["available", "missing", *sorted(STATES)]},
              "methods": dict(sorted(methods.items())),
              "method_states": [{"method": method, "state": state, "count": count}
                                for (method, state), count in sorted(cross.items())]}
    kind = definition["type"]
    if kind in ("number", "integer"):
        numbers = [item["result"] for item in available
                   if type(item["result"]) in (int, float) and math.isfinite(item["result"])]
        quartiles = [quantile(numbers, value) for value in (0.25, 0.5, 0.75)]
        if backend == "pandas" and numbers:
            import pandas as pd
            quartiles = pd.Series(numbers, dtype="float64").quantile([0.25, 0.5, 0.75], interpolation="linear").tolist()
        report["numeric"] = {"unit": definition.get("unit"), "count": len(numbers),
                             "invalid_count": k - len(numbers), "minimum": min(numbers) if numbers else None,
                             "maximum": max(numbers) if numbers else None,
                             "q1": quartiles[0], "median": quartiles[1], "q3": quartiles[2]}
        extremes = {min(numbers), max(numbers)} if numbers else set()
        report["extremes"] = [{"subject_id": item["subject_id"], "capture_id": item["capture_id"],
                               "value": item["result"], "source": item["source"]}
                              for item in available if type(item["result"]) in (int, float)
                              and item["result"] in extremes]
    elif kind in ("enum", "boolean", "string_list", "string"):
        frequencies, values = Counter(), {}
        for item in available:
            members = item["result"] if kind == "string_list" else [item["result"]]
            for key, value in {encoded(member): member for member in members}.items():
                frequencies[key] += 1
                values[key] = value
        report["categorical" if kind != "string" else "exact_text"] = {
            "distinct_count": len(frequencies), "multi_value": kind == "string_list",
            "values": [{"value": values[key], "count": count,
                        "population_fraction": count / n if n else None,
                        "available_fraction": count / k if k else None}
                       for key, count in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))],
            "unobserved_vocabulary": [value for value in definition.get("allowed_values", [])
                                      if encoded(value) not in frequencies]}
    return report


def build_profile(facts, subjects, profile, provenance, backend="python"):
    """Each partition counts subjects (or subject observations) once per context."""
    if backend not in ("python", "pandas"):
        raise ValueError("Unknown report backend.")
    fields, groups = [], []
    for population in ("current", "history"):
        selected = [item for item in facts if population == "history" or item["is_current"]]
        kinds = sorted({item["subject_kind"] for item in subjects}) or ["listing"]
        for kind in kinds:
            kind_facts = [item for item in selected if item["subject_kind"] == kind]
            units = {(item["subject_id"], item["capture_id"]): item for item in kind_facts}
            sources = sorted({item["source_key"] for item in units.values()})
            by_field = defaultdict(list)
            for item in kind_facts:
                by_field[item["field"]].append(item)
            for source in [None, *sources]:
                population_units = {key: item for key, item in units.items()
                                    if source is None or item["source_key"] == source}
                group_cells = defaultdict(Counter)
                for name, definition in sorted(profile["attributes"].items()):
                    values = by_field[name]
                    contexts = {encoded(item["context"]): item["context"] for item in values}
                    if not contexts:
                        context = {key: definition.get(key) for key in ("scope", "qualifier", "basis")}
                        contexts[encoded(context)] = context
                    for context_key, context in sorted(contexts.items()):
                        present = {(item["subject_id"], item["capture_id"]): item for item in values
                                   if encoded(item["context"]) == context_key
                                   and (source is None or item["source_key"] == source)}
                        counted = [present.get(key, dict(item, result=None, method=None, source=[]))
                                   for key, item in population_units.items()]
                        stats = statistics(counted, definition, backend)
                        fields.append({"population": population, "subject_kind": kind, "source_key": source,
                                       "field": name, "column": column(name, definition), "context": context,
                                       "unit_of_count": "subjects" if population == "current" else "subject_observations",
                                       **stats})
                        group_cells[name.split(".")[0]].update(stats["states"])
                for group, counts in sorted(group_cells.items()):
                    total = sum(counts.values())
                    groups.append({"population": population, "subject_kind": kind, "source_key": source,
                                   "group": group, "unit_of_count": "subject_field_context_cells",
                                   "N": total, "K": counts["available"], "states": dict(counts),
                                   "coverage": counts["available"] / total if total else None})
    times = sorted({item["capture_recorded_at"] for item in facts if item.get("capture_recorded_at")})
    current = {item["subject_id"]: item["subject_kind"] for item in facts if item["is_current"]}
    return {"report_format_version": "category-silver-profile-2", "provenance": provenance,
            "schema_version": profile["schema_version"], "population_sha256": digest(subjects),
            "subject_counts": dict(Counter(current.values())),
            "historical_subject_counts": dict(Counter(item["subject_kind"] for item in subjects)),
            "capture_recorded_time_coverage": {"first": times[0] if times else None, "last": times[-1] if times else None},
            "fields": fields, "groups": groups}


def render_profile(report):
    lines = ["# Silver schema profile", "", "Current source subjects; missing and explicit states remain in the denominator.",
             "Categorical lists count each member once per subject. Qualified numeric facts have separate rows.", "",
             "| Field | Subject | Context | Available / N | Values or range |", "| --- | --- | --- | --- | --- |"]
    for item in report["fields"]:
        if item["population"] != "current" or item["source_key"] is not None:
            continue
        if "numeric" in item:
            summary = str(item["numeric"]["minimum"]) + " to " + str(item["numeric"]["maximum"])
        else:
            values = item.get("categorical", item.get("exact_text", {}))
            summary = str(values.get("distinct_count", 0)) + " distinct; " + ", ".join(
                str(value["value"])[:60] + " (" + str(value["count"]) + ")" for value in values.get("values", [])[:5])
        context = ", ".join(str(value) for value in item["context"].values() if value is not None)
        cells = [item["column"], item["subject_kind"], context, str(item["K"]) + " / " + str(item["N"]), summary]
        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    lines += ["", "Full frequencies, methods, explicit states, source partitions, history and extremes are in schema-profile.json.", ""]
    return "\n".join(lines)
