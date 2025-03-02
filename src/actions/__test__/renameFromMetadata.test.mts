import test, { afterEach } from "node:test";
import { vol } from "memfs";
import assert from "node:assert";

afterEach(() => {
  vol.reset();
});
test("normal", async (t) => {
  const realFs = await import("node:fs");
  const book = realFs.readFileSync(
    new URL("../../../sample-books/1Q84.epub", import.meta.url),
  );
  const { fs } = await import("memfs");
  t.mock.module("node:fs", {
    namedExports: fs,
    defaultExport: fs,
  });
  vol.fromJSON({
    "/awesome.epub": book,
  });
  const { default: rename } = await import("../renameFromMetadata.mjs");
  const newFilepath = await rename("/awesome.epub", { dry: false });
  assert.strictEqual(
    newFilepath,
    "/Murakami, Haruki - 1Q84 (Vintage International).epub",
  );
});
