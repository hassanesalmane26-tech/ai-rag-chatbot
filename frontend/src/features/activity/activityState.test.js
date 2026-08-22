import assert from "node:assert/strict";
import test from "node:test";
import { formatActivityTime } from "./activityState.js";

test("formats valid Workspace activity dates without exposing raw metadata", () => {
  assert.match(formatActivityTime("2026-08-22T10:00:00Z"), /2026/);
});

test("uses a recoverable label for invalid activity dates", () => {
  assert.equal(formatActivityTime("not-a-date"), "Date indisponible");
});
