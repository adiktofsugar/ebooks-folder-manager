import assert from "node:assert";
import test, { mock } from "node:test";

test("normal", async () => {
  const realFs = await import("node:fs");
  const book = realFs.readFileSync(
    new URL("../../../sample-books/1Q84.epub", import.meta.url),
  );
  const { vol, fs } = await import("memfs");
  mock.module("node:fs", {
    namedExports: fs,
    defaultExport: fs,
  });
  vol.fromJSON({
    "/awesome.epub": book,
  });
  const { default: getMetadata } = await import("../getMetadata.mjs");
  const { title } = await getMetadata("/awesome.epub");
  assert.strictEqual(title, "1Q84 (Vintage International)");
});
