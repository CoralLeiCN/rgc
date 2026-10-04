# Model handoff

The [standard Silver v2 reference](standard-silver.md) owns default `process`,
four-contract authoring, durable human corrections and generated reports. This
reference preserves the historical v1 interface and applicable research guidance;
use `process --legacy` for v1 outputs. Gold owns model policy in the v2 workflow.

Model design and input preparation belong to the downstream
[Silver-to-Gold procedure](silver-to-gold.md). Category-processing checks available
raw data and a generated schema, then finishes at reviewed Silver. This reference
remains a compatibility link for existing callers.
