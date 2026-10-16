import * as duckdb from "npm:@duckdb/duckdb-wasm";
import {DataType, util} from "npm:apache-arrow@17.0.0";
import {FileAttachment} from "observablehq:stdlib";
import MarkdownIt from "npm:markdown-it@14.3.3";

let connection;
const markdown = new MarkdownIt({html: false});

async function openWarehouse() {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts(${JSON.stringify(bundle.mainWorker)});`], {type: "text/javascript"})
  );
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING), worker);
  try {
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  } finally {
    URL.revokeObjectURL(workerUrl);
  }
  const bytes = await FileAttachment("./warehouse.duckdb").arrayBuffer();
  await db.registerFileBuffer("warehouse.duckdb", new Uint8Array(bytes));
  await db.open({path: "warehouse.duckdb", accessMode: duckdb.DuckDBAccessMode.READ_ONLY});
  return {db, conn: await db.connect()};
}

export function getDB() {
  connection ??= openWarehouse();
  return connection;
}

function plainValue(value, type) {
  if (value !== null && (DataType.isDate(type) || DataType.isTimestamp(type))) {
    return new Date(value);
  }
  if (typeof value === "bigint") return Number(value);
  if (value !== null && DataType.isDecimal(type)) return util.bigNumToNumber(value, type.scale);
  return value;
}

export async function query(sql, params = []) {
  const {conn} = await getDB();
  let result;
  if (params.length) {
    const statement = await conn.prepare(sql);
    try {
      result = await statement.query(...params);
    } finally {
      await statement.close();
    }
  } else {
    result = await conn.query(sql);
  }
  return result.toArray().map(row => Object.fromEntries(
    result.schema.fields.map(field => [field.name, plainValue(row[field.name], field.type)])
  ));
}

export async function narrative(targetId, axis, sectionKey) {
  const rows = await query(
    "SELECT body_md, tier FROM narratives WHERE target_id = ? AND axis = ? AND section_key = ?",
    [targetId, axis, sectionKey]
  );
  const row = rows[0] ?? {body_md: "No narrative has been generated for this card.", tier: null};
  const body = document.createElement("span");
  body.innerHTML = markdown.renderInline(row.body_md);
  return {body, tier: row.tier};
}

export async function axisConfidence(targetId, axis) {
  const rows = await query(
    "SELECT signal_completeness_pct, confidence_class, missing_sources FROM axis_confidence WHERE target_id = ? AND axis = ?",
    [targetId, axis]
  );
  return rows[0] ?? {signal_completeness_pct: 0, confidence_class: "low", missing_sources: null};
}
