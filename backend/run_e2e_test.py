"""End-to-end: merge all DDL files + inject curated relations → generate
semantic, join-consistent data → export CSV per source file into output/.

Runs fully in-process (no HTTP server). Set DATAFORGE_LLM_API_KEY (and base_url
/ model) in the environment and pass --ai to enable the AI seed pass.
"""
import sys, io, zipfile, pathlib

sys.path.insert(0, ".")

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.services.parse_service import ParseService
from app.services.generate_service import GenerateService
from app.services.export_service import ExportService

ROWS_PER_TABLE = 100
USE_AI = "--ai" in sys.argv

ddl_dir = pathlib.Path("../test_ddl")
out_dir = pathlib.Path("../output")
out_dir.mkdir(exist_ok=True)

sql_files = sorted(ddl_dir.glob("*.sql"))
sources = [p.read_text(encoding="utf-8") for p in sql_files]
relation_graph = (ddl_dir / "schema_graph.cypher").read_text(encoding="utf-8")
# Map each table name to its source file (for foldered CSV output).
table_file: dict[str, str] = {}

registry = SchemaRegistry()
db = DuckDBClient(path=":memory:")
parse_svc = ParseService(registry=registry, db=db)
gen_svc = GenerateService(registry=registry, db=db)
export_svc = ExportService(registry=registry, db=db)

# Track which table came from which file (parse each individually for the map).
from app.core.ddl_parser import DDLParser
_p = DDLParser()
for sf, src in zip(sql_files, sources):
    try:
        for t in _p.parse(src, dialect="mysql").tables:
            table_file.setdefault(t.name, sf.stem)
    except Exception:
        pass

print("=== Step 1: merge DDL + inject relations ===")
schema = parse_svc.parse_ddl_files(sources, dialect="mysql", relation_graph=relation_graph)
fk_total = sum(len(t.foreign_keys) for t in schema.tables)
print(f"  {len(schema.tables)} tables, {fk_total} FK edges injected")

print(f"\n=== Step 2: generate {ROWS_PER_TABLE} rows/table (ai={USE_AI}) ===")
row_counts = {t.name: ROWS_PER_TABLE for t in schema.tables}
result = gen_svc.generate(schema.id, row_counts, ai_enabled=USE_AI)
print(f"  generated {sum(m['generated'] for m in result['tables'].values())} rows, "
      f"ai_used={result['ai_used']}, ai_specs={result['generation_meta'].get('ai_specs', 0)}")

print("\n=== Step 3: join closure check ===")
import app.core.relation_parser as rp
relations = rp.parse_schema_graph(relation_graph)
solver_targets = {}
from app.generator.constraint import ConstraintSolver
solver = ConstraintSolver(schema)
checked, closed, total = set(), 0, 0
for rel in relations:
    ck = (rel.child_table, rel.child_col)
    tgt = solver.fk_target(*ck)
    if not tgt or ck in checked:
        continue
    checked.add(ck)
    ptbl, pcol = tgt
    try:
        n_total = db.query(f'SELECT COUNT(*) n FROM "{rel.child_table}" WHERE "{rel.child_col}" IS NOT NULL')[0]["n"]
        if not n_total:
            continue
        n_match = db.query(
            f'SELECT COUNT(*) n FROM "{rel.child_table}" c JOIN "{ptbl}" p '
            f'ON c."{rel.child_col}" = p."{pcol}"'
        )[0]["n"]
        total += 1
        if n_match >= n_total:
            closed += 1
    except Exception:
        pass
print(f"  fully-closed joins: {closed}/{total}")

print("\n=== Step 4: export CSV per source file ===")
zip_bytes = export_svc.export(schema.id, "csv")
written = 0
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
    for entry in zf.namelist():
        tname = entry.rsplit(".", 1)[0]
        sub = out_dir / table_file.get(tname, "_misc")
        sub.mkdir(exist_ok=True)
        with zf.open(entry) as s, open(sub / entry, "wb") as d:
            d.write(s.read())
        written += 1
print(f"  wrote {written} CSV files under {out_dir.resolve()}")
print("\nDone.")
