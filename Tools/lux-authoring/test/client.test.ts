import assert from "node:assert/strict";
import test from "node:test";
import { createTextTask, uploadOwnedFile, withKeyFallback } from "../src/client.ts";

test("creation is blocked before any API request without explicit approval", async () => {
  await assert.rejects(createTextTask("test", { prompt: "original test object" }, false), /Creation blocked/);
});

test("missing API key stops an approved creation before an official request", async () => {
  delete process.env.AHOLO_API_KEY;
  delete process.env.AHOLO_API_KEY_BACKUP;
  await assert.rejects(createTextTask("test", { prompt: "original test object" }, true), /AHOLO_API_KEY/);
});

test("upload requires ownership confirmation before reading or sending a file", async () => {
  await assert.rejects(uploadOwnedFile("test", "not-read.txt", false), /Upload blocked/);
});

test("backup key is used for quota errors but not network errors", async () => {
  const originalPrimary = process.env.AHOLO_API_KEY;
  const originalBackup = process.env.AHOLO_API_KEY_BACKUP;
  process.env.AHOLO_API_KEY = "primary-test";
  process.env.AHOLO_API_KEY_BACKUP = "backup-test";
  try {
    const attempts: string[] = [];
    const result = await withKeyFallback(async (apiKey) => {
      attempts.push(apiKey);
      if (apiKey === "primary-test") {
        throw Object.assign(new Error("insufficient credits"), { statusCode: 402 });
      }
      return "created";
    });
    assert.equal(result, "created");
    assert.deepEqual(attempts, ["primary-test", "backup-test"]);

    const networkAttempts: string[] = [];
    await assert.rejects(withKeyFallback(async (apiKey) => {
      networkAttempts.push(apiKey);
      throw new Error("network offline");
    }), /network offline/);
    assert.deepEqual(networkAttempts, ["primary-test"]);
  } finally {
    if (originalPrimary === undefined) delete process.env.AHOLO_API_KEY;
    else process.env.AHOLO_API_KEY = originalPrimary;
    if (originalBackup === undefined) delete process.env.AHOLO_API_KEY_BACKUP;
    else process.env.AHOLO_API_KEY_BACKUP = originalBackup;
  }
});
