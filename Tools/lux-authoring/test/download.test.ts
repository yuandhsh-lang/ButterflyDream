import assert from "node:assert/strict";
import test from "node:test";
import { checkMagicBytes, outputEntries } from "../src/download.ts";

test("output parsing preserves actual outputs and skips unrequested slots", () => {
  const entries = outputEntries([
    { content: "NOT_REQUESTED" },
    { content: "https://example.com/model.glb?signature=secret" },
    { content: JSON.stringify(["https://example.com/front.png", "https://example.com/back.png"]) },
    { content: "text result" },
  ]);
  assert.equal(entries.length, 4);
  assert.equal(entries[0].url, "https://example.com/model.glb?signature=secret");
  assert.equal(entries[3].url, undefined);
});

test("GLB and ZIP magic validation reject HTML and invalid payloads", () => {
  assert.doesNotThrow(() => checkMagicBytes(new TextEncoder().encode("glTF-data"), ".glb"));
  assert.doesNotThrow(() => checkMagicBytes(new Uint8Array([0x50, 0x4b, 3, 4]), ".zip"));
  assert.throws(() => checkMagicBytes(new TextEncoder().encode("<html>"), ".glb"), /magic/);
  assert.throws(() => checkMagicBytes(new TextEncoder().encode("glTF"), ".zip"), /magic/);
});
