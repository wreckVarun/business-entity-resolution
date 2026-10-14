"""Builds notebooks/walkthrough.ipynb (run it, then execute the notebook with nbconvert)."""
from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
    md("""# Business entity resolution: walkthrough

Amazon ML Challenge 2026 dataset. Three sources of business records (name, address, country). Source 1 is
deduplicated; for each Source 1 business, find every Source 2/3 record that is the same business.
Scored with entity-level F0.5 (precision counts twice as much as recall).

This notebook reads the Parquet files and the reports written by the pipeline (`run_all.sh`), so it runs in seconds."""),
    code("""import json, sys
from pathlib import Path
import duckdb, pandas as pd
from IPython.display import Image, Markdown, display

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
PQ, REP = ROOT / "data" / "parquet", ROOT / "reports"
con = duckdb.connect()
pd.set_option("display.max_colwidth", 90)"""),
    md("## 1. The data"),
    code("""con.execute(f'''
SELECT split, src, country, count(*) records FROM (
  SELECT 'train' split, 'S1' src, country FROM '{PQ}/train_s1.parquet' UNION ALL
  SELECT 'train', 'S2', country FROM '{PQ}/train_s2.parquet' UNION ALL
  SELECT 'train', 'S3', country FROM '{PQ}/train_s3.parquet' UNION ALL
  SELECT 'test', 'S1', country FROM '{PQ}/test_s1.parquet' UNION ALL
  SELECT 'test', 'S2', country FROM '{PQ}/test_s2.parquet' UNION ALL
  SELECT 'test', 'S3', country FROM '{PQ}/test_s3.parquet')
GROUP BY ALL ORDER BY split DESC, src, country''').fetchdf().pivot_table(index=['split','src'], columns='country', values='records')"""),
    md("""**Three facts from the labels that shape the whole design**

1. Each Source 2/3 record is matched to *at most one* Source 1 business, so a record can be assigned to its single best business.
2. Most businesses have several matches (3.5 on average), only ~5.6% have none, so predicting nothing is rarely right.
3. About a quarter of Source 2/3 records match nothing: they are near-duplicate distractors (same name, different house number or town)."""),
    code("""con.execute(f'''CREATE OR REPLACE TABLE gt AS SELECT source1_entity_id s1, unnest(CASE WHEN matched_entity_ids IS NULL OR matched_entity_ids = ''
  THEN [NULL] ELSE string_split(matched_entity_ids, ',') END) m FROM '{PQ}/train_gt.parquet' ''')
per = con.execute("SELECT nm AS matches_per_business, count(*) businesses FROM (SELECT s1, count(m) nm FROM gt GROUP BY s1) GROUP BY 1 ORDER BY 1").fetchdf()
per['share'] = (per.businesses / per.businesses.sum()).round(4)
display(per)
print('records owned by more than one Source 1 business:',
      con.execute("SELECT count(*) FROM (SELECT m FROM gt WHERE m IS NOT NULL GROUP BY m HAVING count(DISTINCT s1) > 1)").fetchone()[0])"""),
    md("## 2. What the noise looks like"),
    code("""con.execute(f'''
WITH pick AS (SELECT entity_id FROM '{PQ}/train_s1.parquet' WHERE country = 'India' USING SAMPLE 3 ROWS (reservoir, 5))
SELECT a.business_name s1_name, a.business_address s1_address, b.business_name match_name, b.business_address match_address
FROM pick JOIN '{PQ}/train_s1.parquet' a USING (entity_id) JOIN gt ON gt.s1 = a.entity_id
JOIN (SELECT * FROM '{PQ}/train_s2.parquet' UNION ALL SELECT * FROM '{PQ}/train_s3.parquet') b ON b.entity_id = gt.m''').fetchdf()"""),
    md("""## 3. Normalisation

Transliteration to ASCII, abbreviation tables, 'trading as' splitting, and a phonetic skeleton so that a name written
in an Indian script gets the same key as its English spelling."""),
    code("""from normalize import normalize_record
examples = [("Indian Care Private Limited", "Itwari Mohalla Shahdol, Shahdol, Madhya Pradesh"),
            ("इंडियन केयर प्राइवेट लिमिटेड", "#917/8 Itwari Mohalla Shahdol, Shahdol, Umaria, MP"),
            ("Nexjaxlyra trading as Indian Care Private Limited", "Itwari Mohalla Shahdol, Shahdol, Madhya Pradesh"),
            ("Montari Spíre", "#34184 Tanglewood Pass, SAN TAN Valley CITY, Arizona")]
pd.DataFrame([{"name": n, **normalize_record(n, a)} for n, a in examples])[["name", "name_core", "name_phon", "addr_words", "house_no"]]"""),
    md("""## 4. Blocking

Ten key families (name word, phonetic word, address word pair, name+address word, whole name, name without spaces,
name/address word + house number). A key is used only if at most 200 (whole-name keys: 1,000) target records carry it.
Candidates are ranked by the summed IDF of shared keys and the top 40 per business are kept."""),
    code("""b = json.loads((REP / "blocking.json").read_text())
display(pd.DataFrame(b["by_top_k"]))
display(Image(str(REP / "figures" / "blocking_recall.png")))"""),
    md("## 5. Model and decision rule"),
    code("""v = json.loads((REP / "validation.json").read_text())
display(pd.DataFrame([{"what": "validation (held-out businesses)", **v["best"]},
                      {"what": "perfect classifier on the same candidates", **v["blocking_ceiling"]}]))
display(pd.DataFrame(v["by_country"]).T)
display(Image(str(REP / "figures" / "threshold_curve.png")))
display(Image(str(REP / "figures" / "feature_importance.png")))"""),
    md("## 6. Where it still goes wrong"),
    code("""display(Markdown((REP / "error_analysis.md").read_text().split("## False links")[0]))"""),
    md("## 7. Does it transfer to a country it has never seen?"),
    code("""p = REP / "leave_one_country_out.json"
if p.exists():
    rows = json.loads(p.read_text())
    display(pd.DataFrame([{"held out": r["held_out_country"], "F0.5 trained with it": r["trained_with_it"]["f05"],
                           "F0.5 never seen": r["trained_without_it"]["f05"]} for r in rows]))
    display(Image(str(REP / "figures" / "leave_one_country_out.png")))"""),
]
out = Path(__file__).with_name("walkthrough.ipynb")
nbf.write(nb, out)
print("wrote", out)
