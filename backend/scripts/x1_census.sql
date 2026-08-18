-- X1 Stage 0 census — run against the dev database.
-- Headline number is query 4: register_only rows hiding useful text.

-- 1. total
SELECT count(*) AS total FROM source_documents;

-- 2. by class
SELECT document_class, count(*) FROM source_documents
GROUP BY 1 ORDER BY 2 DESC;

-- 3. by ingest_mode
SELECT ingest_mode, count(*) FROM source_documents GROUP BY 1;

-- 4. THE KEY NUMBER: register_only rows that are hiding useful text
SELECT count(*) AS suppressed_with_text
FROM source_documents sd
WHERE sd.ingest_mode = 'register_only'
  AND length(btrim(sd.normalized_content)) >= 200;

-- 5. docs with text but zero chunks (the same wound, seen from the other side)
SELECT count(*) AS text_no_chunks
FROM source_documents sd
WHERE length(btrim(sd.normalized_content)) >= 200
  AND NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id);

-- 6. classes outside the declared Literal (known: inbox_pending, corpus_catalog)
SELECT document_class, count(*) FROM source_documents
WHERE document_class NOT IN (
  'unknown','contract','specification','tender_submission','trr','evaluation',
  'rft','addendum','eoi','tep','drawing','report','certificate',
  'correspondence','schedule','reference_guide','doctrine','planning_instrument'
) GROUP BY 1;

-- 7. legacy procurement classes (Stage 8 workload)
SELECT count(*) FROM source_documents
WHERE document_class IN ('tep','eoi','rft','addendum','tender_submission','evaluation','trr');

-- 8. null content_hash (blocks Stage 5 override key — see OD-3)
SELECT count(*) FROM source_documents WHERE content_hash IS NULL;
