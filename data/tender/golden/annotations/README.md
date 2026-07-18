Annotations directory — one JSON file per golden document, named `{document_id}.json`, conforming to `manifest.yaml` annotation_schema.

Flagship speed-fixture annotations (Enmore / Kaposi / NexusBuilt) seed T0 synonyms via:

```bash
python data/tender/tools/seed_synonyms_from_golden.py
python data/tender/tools/expand_synonyms.py
python data/tender/tools/validate.py
```
