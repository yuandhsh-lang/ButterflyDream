import assert from "node:assert/strict";
import test from "node:test";
import { createLux3dClient } from "@manycore/aholo-sdk-lux3d";

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

test("official SDK textTo3d uses the documented task endpoint and maps numeric task ID", async () => {
  let observedUrl = "";
  let observedBody = "";
  const client = createLux3dClient({
    apiKey: "unit-test-not-a-real-key",
    fetch: async (input, init) => {
      observedUrl = String(input);
      observedBody = String(init?.body);
      return response({ c: "0", d: 42, m: "" });
    },
  });
  const taskId = await client.textTo3d.create({ prompt: "original gate", version: "G1", outputFormat: ["glb"] });
  assert.equal(taskId, 42);
  assert.ok(observedUrl.endsWith("/generate/text-to-3d/task/create"));
  assert.equal(JSON.parse(observedBody).prompt, "original gate");
});

test("official SDK articulation and task retrieval map documented responses", async () => {
  const urls: string[] = [];
  const client = createLux3dClient({
    apiKey: "unit-test-not-a-real-key",
    fetch: async (input) => {
      urls.push(String(input));
      if (String(input).includes("articulation-animation")) return response({ c: "0", d: 43, m: "" });
      return response({ c: "0", d: { taskId: 43, status: 3, outputs: [{ content: "https://example.com/result.glb?signed=mock" }] }, m: "" });
    },
  });
  assert.equal(await client.articulationAnimation.create({ glbUrl: "https://example.com/original.glb", prompt: "open the gate" }), 43);
  const task = await client.tasks.retrieve(43);
  assert.equal(task.status, 3);
  assert.equal(task.taskId, 43);
  assert.ok(urls[0].endsWith("/articulation-animation/task/create"));
  assert.ok(urls[1].includes("/generate/task/get"));
});
