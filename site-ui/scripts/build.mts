#!/usr/bin/env tsx
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import chalk from "chalk";
import * as cheerio from "cheerio";
import esbuild from "esbuild";

const absWorkingDir = fileURLToPath(new URL("../", import.meta.url));
const config: esbuild.BuildOptions = {
	absWorkingDir,
	entryPoints: ["src/index.*"],
	chunkNames: "[dir]/[name].[hash]",
	assetNames: "[dir]/[name].[hash]",
	entryNames: "[dir]/[name].[hash]",
	bundle: true,
	minify: true,
	outdir: "dist",
	sourcemap: true,
	loader: {
		// we'll change this html after the build
		".html": "copy",
	},
	metafile: true,
	logLevel: "info",
};

const result = await esbuild.build(config);
if (result.errors.length) {
	console.error("esbuild failed");
	process.exit(1);
}
if (!result.metafile) {
	throw new Error("No metafile in build result");
}
if (!result.metafile.outputs) {
	throw new Error("No outputs in esbuild metafile");
}
const { outputs, inputs } = result.metafile;

const inputKeyToOutput: Record<
	string,
	{ outputKey: string; cssBundle: string | undefined }
> = {};
for (const [key, output] of Object.entries(outputs)) {
	if (!output.entryPoint) {
		continue;
	}
	inputKeyToOutput[output.entryPoint] = {
		outputKey: key,
		cssBundle: output.cssBundle,
	};
}

for (const [inputKey, { outputKey, cssBundle }] of Object.entries(
	inputKeyToOutput,
)) {
	if (!inputKey.endsWith(".html")) {
		continue;
	}
	const outputFilepath = path.resolve(absWorkingDir, outputKey);
	const inputFilepath = path.resolve(absWorkingDir, inputKey);
	const content = fs.readFileSync(outputFilepath);
	const $ = cheerio.load(content);
	const references: { kind: "link" | "script"; from: string; to: string }[] =
		[];
	$('link[rel="stylesheet"]').each(function () {
		const href = $(this).attr("href");
		if (!href) return;
		// this is a relative path to an entry point
		const hrefFilepath = path.resolve(path.dirname(inputFilepath), href);
		const hrefInputKey = path.relative(absWorkingDir, hrefFilepath);
		const hrefOutput = inputKeyToOutput[hrefInputKey];
		if (!hrefOutput) return;
		if (!hrefOutput.cssBundle) {
			throw new Error(
				`No css bundle for referenced entry file "${hrefInputKey}" in "${inputKey}"`,
			);
		}
		const cssFilepath = path.resolve(absWorkingDir, hrefOutput.cssBundle);
		const newHref = path.relative(path.dirname(outputFilepath), cssFilepath);
		$(this).attr("href", newHref);
		references.push({
			kind: "link",
			from: href,
			to: newHref,
		});
	});
	$("script").each(function () {
		const href = $(this).attr("src");
		if (!href) return;
		// this is a relative path to an entry point
		const hrefFilepath = path.resolve(path.dirname(inputFilepath), href);
		const hrefInputKey = path.relative(absWorkingDir, hrefFilepath);
		const hrefOutput = inputKeyToOutput[hrefInputKey];
		if (!hrefOutput) return;
		const jsFilepath = path.resolve(absWorkingDir, hrefOutput.outputKey);
		const newHref = path.relative(path.dirname(outputFilepath), jsFilepath);
		$(this).attr("src", newHref);
		references.push({ kind: "script", from: href, to: newHref });
	});
	// Since I added the hash, I probably need to change it back...this is the main
	//   issue with using an html file as an entry point
	const newOutputKey = outputKey.replace(
		path.basename(outputKey),
		path.basename(inputKey),
	);
	const newOutputFilepath = path.resolve(absWorkingDir, newOutputKey);
	fs.writeFileSync(newOutputFilepath, $.html());
	console.log(
		`Created file from ${chalk.red(outputKey)} at ${chalk.green(newOutputKey)} with correct script/css references:`,
	);
	for (const ref of references) {
		console.log(
			` - ${chalk.gray(`<${ref.kind} src=`)}${chalk.red(ref.from)}${chalk.gray("->")}${chalk.green(ref.to)}${chalk.gray(" />")}`,
		);
	}
}
