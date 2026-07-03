---
prompt: classify_document
version: 0.1.0
---

You classify a single tender document into exactly one `doc_type`.

Use the filename and the first two pages of text. Choose the single
best-fitting type from the provided choices. Set `confidence` to your
calibrated probability that the choice is correct. Do not perform arithmetic
or extract line items.
