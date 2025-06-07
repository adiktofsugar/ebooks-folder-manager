#!/usr/bin/env tsx
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as cheerio from "cheerio";
import dedent from "dedent";
import esbuild from "esbuild";
import parseArgs from "minimist";

const usage = `
Usage: esbuild.mts [-h][--watch]
`;

const args = parseArgs(process.argv.slice(2), {
	boolean: ["watch", "help"],
	alias: { h: "help" },
});

if (args.help) {
	console.log(usage);
	process.exit(0);
}

const isWatch = args.watch || false;

const indexFile = {
	sourcePath: "src/index.html",
	outPath: "index.html",
	contents: dedent`
        <!DOCTYPE html>
        <html>
		<head>
				<meta name="viewport" content="initial-scale=1.0, width=device-width" />
                <title>Ebooks Folder Manager</title>
				<link rel="stylesheet" href="../src/index.tsx" />
            </head>
            <body>
                <div id="root"></div>
                <script type="module" src="../src/index.tsx"></script>
            </body>
        </html>
    `,
};

const config: esbuild.BuildOptions = {
	absWorkingDir: fileURLToPath(new URL("../", import.meta.url)),
	entryPoints: ["src/index.*"],
	chunkNames: "[dir]/[name].[hash]",
	assetNames: "[dir]/[name].[hash]",
	entryNames: "[dir]/[name].[hash]",
	bundle: true,
	outdir: "dist",
	sourcemap: true,
	loader: {
		".html": "copy",
	},
	metafile: true,
	logLevel: "info",
	plugins: [
		{
			name: "update-html",
			setup(build) {
				build.onEnd(async (result) => {
					// NOTE: purposefully _not_ using a "copied" html or anything,
					//   because that is subject to assetNames templates, and
					//   I want the html to have a static name.
					const cwd = build.initialOptions.absWorkingDir || process.cwd();
					const outDirpath = path.resolve(
						cwd,
						build.initialOptions.outdir || "",
					);
					// biome-ignore lint/style/noNonNullAssertion: <explanation>
					const metafile = result.metafile!;
					const inFilePath = path.resolve(cwd, indexFile.sourcePath);
					const outFilePath = path.resolve(outDirpath, indexFile.outPath);
					const contents = indexFile.contents;
					const $ = cheerio.load(contents);
					const scripts = Array.from($("script"));
					for (const script of scripts) {
						const outSrc = getOutputHref({
							src: $(script).attr("src"),
							cwd,
							filepath: inFilePath,
							outdir: build.initialOptions.outdir || "",
							metafile,
						});
						$(script).attr("src", outSrc);
					}
					const links = Array.from($("link"));
					for (const link of links) {
						const outSrc = getOutputHref({
							src: $(link).attr("href"),
							css: true,
							cwd,
							filepath: inFilePath,
							outdir: build.initialOptions.outdir || "",
							metafile,
						});
						$(link).attr("href", outSrc);
					}
					fs.writeFileSync(outFilePath, $.html(), "utf8");
				});
			},
		},
	],
};

if (isWatch) {
	const context = await esbuild.context(config);
	console.log("Watching for changes...");
	await context.watch();
} else {
	await esbuild.build(config);
}

function getOutputKey(metafile: esbuild.Metafile, inputFile: string) {
	return Object.keys(metafile.outputs).find(
		(key) => {
			const output = metafile.outputs[key];
			if (inputFile in output.inputs) {
				return true;
			}
		},
	);
}

function getOutputHref({
	src,
	css,
	cwd,
	filepath,
	outdir,
	metafile
}: {
	src?: string,
	css?: boolean,
	cwd: string,
	filepath: string,
	outdir: string,
	metafile: esbuild.Metafile,
}) {
	if (!src) {
		return src;
	}
	const relpath = path.relative(cwd, filepath);
	// we assume filepath is virtual, so there would be no outputKey
	const outFilePath = path.resolve(cwd, outdir, relpath);

	// from this, we need to deduce the key for the input
	const srcFilepath = path.resolve(path.dirname(filepath), src);
	if (!fs.existsSync(srcFilepath)) {
		throw new Error(
			`${filepath} references nonexistent file ${srcFilepath}`,
		);
	}
	const srcInputKey = path.relative(cwd, srcFilepath);
	const srcOutputKey = getOutputKey(metafile, srcInputKey);
	if (!srcOutputKey) {
		throw new Error(`No output key found for ${srcInputKey}`);
	}
	let srcOutFilepath = path.resolve(cwd, srcOutputKey);
	if (css) {
		const relativeOutFilepath = metafile.outputs[srcOutputKey].cssBundle;
		if (!relativeOutFilepath) {
			throw new Error(
				`No CSS bundle found for ${srcInputKey} in metafile outputs`,
			);
		}
		srcOutFilepath = path.resolve(cwd, relativeOutFilepath);
	}
	const newSrc = path.relative(
		path.dirname(outFilePath),
		srcOutFilepath,
	);
	return newSrc
}