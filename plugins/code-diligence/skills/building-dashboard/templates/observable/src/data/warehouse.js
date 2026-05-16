import * as duckdb from "@duckdb/duckdb-wasm";

let _cached;

/** Load and cache a DuckDB-WASM connection over the target warehouse. */
export async function getDB() {
  if (_cached) return _cached;
  const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
  const worker_url = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
  );
  const worker = new Worker(worker_url);
  const logger = new duckdb.ConsoleLogger("WARNING");
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(worker_url);

  // The build script copies the active target warehouse to data/warehouse.duckdb.
  const conn = await db.connect();
  await conn.query(`ATTACH 'data/warehouse.duckdb' AS wh (READ_ONLY)`);
  await conn.query("USE wh");
  _cached = { db, conn };
  return _cached;
}

/** Run a SELECT and return rows as plain JS objects. */
export async function query(sql, params = []) {
  const { conn } = await getDB();
  const result = await conn.query(sql, params);
  return result.toArray().map((r) => r.toJSON());
}

/** Fetch the narrative body for a (target_id, axis, section_key). */
export async function narrative(target_id, axis, section_key) {
  const rows = await query(
    `SELECT body_md, tier FROM narratives
     WHERE target_id = ? AND axis = ? AND section_key = ?`,
    [target_id, axis, section_key]
  );
  return rows[0] ?? { body_md: "_(no narrative yet)_", tier: null };
}

/** Confidence chip data for a (target_id, axis). */
export async function axisConfidence(target_id, axis) {
  const rows = await query(
    `SELECT signal_completeness_pct, confidence_class, missing_sources
     FROM axis_confidence WHERE target_id = ? AND axis = ?`,
    [target_id, axis]
  );
  return rows[0] ?? { signal_completeness_pct: 0, confidence_class: "low", missing_sources: null };
}
