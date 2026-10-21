import {table} from "npm:@observablehq/inputs";

export function reportTable(data, options) {
  return table(data, new URLSearchParams(location.search).has("print")
    ? {...options, rows: data.length, maxHeight: undefined}
    : options);
}
