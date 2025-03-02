import assert from "node:assert";
import { vol, fs } from "memfs";
import test, { afterEach } from "node:test";

afterEach(() => {
  vol.reset();
});

test("normal", async (t) => {
  const realFs = await import("node:fs");
  const book = realFs.readFileSync(
    new URL("../../../sample-books/1Q84.epub", import.meta.url),
  );
  t.mock.module("node:fs", {
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

test("opf prefixed elements", async (t) => {
  const realFs = await import("node:fs");
  const book = realFs.readFileSync(
    new URL(
      "../../../sample-books/Interesting Times - Terry Pratchett.epub",
      import.meta.url,
    ),
  );
  t.mock.module("node:fs", {
    namedExports: fs,
    defaultExport: fs,
  });
  vol.fromJSON({
    "/awesome.epub": book,
  });
  const { default: getMetadata } = await import("../getMetadata.mjs");
  const { title } = await getMetadata("/awesome.epub");
  assert.strictEqual(title, "Interesting Times");
});
