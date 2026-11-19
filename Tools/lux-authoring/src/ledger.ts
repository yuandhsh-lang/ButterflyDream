import { mkdirSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";

function secrets(): string[] {
  return [process.env.AHOLO_API_KEY, process.env.AHOLO_API_KEY_BACKUP].filter((value): value is string => Boolean(value));
}

export function redact(value: unknown, extraSecrets: string[] = []): unknown {
  const allSecrets = [...secrets(), ...extraSecrets].filter(Boolean);
  if (typeof value === "string") {
    let text = allSecrets.reduce((current, secret) => current.split(secret).join("[REDACTED]"), value);
    if (/^https?:\/\//i.test(text)) {
      try {
        const url = new URL(text);
        url.username = "";
        url.password = "";
        url.search = "";
        url.hash = "";
        text = url.toString();
      } catch {}
    }
    return text;
  }
  if (Array.isArray(value)) return value.map((item) => redact(item, extraSecrets));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => {
      if (/^(authorization|api[-_]?key|ousToken|uploadKey)$/i.test(key)) return [key, "[REDACTED]"];
      return [key, redact(item, extraSecrets)];
    }));
  }
  return value;
}

export function writeJson(filePath: string, value: unknown): void {
  mkdirSync(path.dirname(filePath), { recursive: true });
  const serialized = JSON.stringify(redact(value), null, 2) + "\n";
  const pending = filePath + ".pending";
  writeFileSync(pending, serialized, "utf8");
  renameSync(pending, filePath);
}

export function errorRecord(error: unknown): Record<string, unknown> {
  if (error instanceof Error) {
    return { name: error.name, message: redact(error.message) };
  }
  return { name: "Error", message: redact(String(error)) };
}
