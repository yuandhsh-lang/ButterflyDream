import assert from "node:assert/strict";
import test from "node:test";
import { redact } from "../src/ledger.ts";
import { taskDirectory, workspacePath } from "../src/paths.ts";

test("redaction removes credentials, URL secrets, and configured API key", () => {
  const previous = process.env.AHOLO_API_KEY;
  process.env.AHOLO_API_KEY = "unit-test-secret";
  try {
    const result = redact({ authorization: "unit-test-secret", nested: { text: "unit-test-secret", url: "https://example.com/model.glb?token=secret#part" } });
    const serialized = JSON.stringify(result);
    assert.equal(serialized.includes("unit-test-secret"), false);
    assert.equal(serialized.includes("token=secret"), false);
    assert.equal(serialized.includes("model.glb"), true);
  } finally {
    if (previous === undefined) delete process.env.AHOLO_API_KEY;
    else process.env.AHOLO_API_KEY = previous;
  }
});

test("workspace paths reject traversal and task directories use safe IDs", () => {
  assert.throws(() => workspacePath("../outside.txt"), /inside the project/);
  assert.ok(taskDirectory("12345").endsWith("12345"));
  assert.throws(() => taskDirectory("../bad"), /Invalid task ID/);
});
