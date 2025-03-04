import fs from "node:fs";
import path from "node:path";
import tmp from "tmp";
import BookMetadata from "./BookMetadata.mjs";
import getMetadata from "./lib/getMetadata.mjs";
import PdfMetadata from "./pdf/PdfMetadata.mjs";
import Logger from "./logger.mjs";
import runK2PdfOpt from "./pdf/runK2PdfOpt.mjs";
import detectDrm from "./epub/detectDrm.mjs";
import removeAdobeDrm from "./epub/removeAdobeDrm.mjs";
import getBackupFilepath from "./lib/getBackupFilepath.mjs";

/**
 * Represents a book. Could be an epub, mobi, pdf, etc.
 * It should cache as much as possible, and be able to apply many fixes
 *   in memory, _then_ save the file.
 */
export default class Book {
  sourceFilepath;
  adobeKeyFilepath;
  newFilepath: string | undefined;
  tmpFilepath: string | undefined;
  metadata: BookMetadata | null | undefined;
  dry: boolean;
  constructor(
    sourceFilepath: string,
    options: { adobeKeyFilepath: string | null | undefined; dry: boolean },
  ) {
    this.sourceFilepath = sourceFilepath;
    this.dry = options.dry;
    this.adobeKeyFilepath = options.adobeKeyFilepath || null;
  }
  getTmpFilepath() {
    if (!this.tmpFilepath) {
      this.tmpFilepath = tmp.tmpNameSync({
        postfix: `-${path.basename(this.sourceFilepath)}`,
      });
      // we do this because it's likely the book is on a remote drive which has miserable
      //   access speed, and tries to sync in the middle of a bunch of operations
      fs.copyFileSync(this.sourceFilepath, this.tmpFilepath);
    }
    return this.tmpFilepath;
  }
  async getMetadata() {
    const tmpFilepath = this.getTmpFilepath();
    if (this.metadata === undefined) {
      const metadata = await getMetadata(tmpFilepath);
      if (metadata) {
        const {
          title,
          creators: creatorsRaw,
          dateOfPublication,
          identifiers,
          primaryLanguage,
        } = metadata;

        let creators: string[];
        if (typeof creatorsRaw === "string") {
          creators = [creatorsRaw];
        } else if (Array.isArray(creatorsRaw)) {
          creators = creatorsRaw;
        } else {
          creators = [];
        }

        let isK2pdfoptVersion = false;
        if (tmpFilepath.endsWith(".pdf")) {
          const pdfMetadata = new PdfMetadata(tmpFilepath);
          ({ isK2pdfoptVersion } = pdfMetadata.getMetadata());
        }

        this.metadata = new BookMetadata({
          title,
          creators,
          dateOfPublication,
          identifiers,
          primaryLanguage,
          isK2pdfoptVersion,
        });
      } else {
        this.metadata = null;
      }
    }
    return this.metadata;
  }
  async printMetadata() {
    const metadata = await this.getMetadata();
    if (metadata) {
      const {
        title,
        creators,
        dateOfPublication,
        identifiers,
        primaryLanguage,
      } = metadata;
      console.log(
        [
          `Title: ${title}`,
          `Authors: ${creators.join(", ")}`,
          dateOfPublication && `Published: ${dateOfPublication}`,
          `Language: ${primaryLanguage}`,
          ...identifiers.map(
            ({ id, scheme }) =>
              `Identifier: ${scheme ? `(${scheme}) ` : ""}${id}`,
          ),
          "----",
        ]
          .filter(Boolean)
          .join("\n"),
      );
    }
  }
  async renameFromMetadata() {
    const metadata = await this.getMetadata();
    if (!metadata) {
      Logger.error(
        "renameFromMetadata - can't get metadata for",
        this.sourceFilepath,
      );
      return;
    }
    const extension = path.extname(this.sourceFilepath).slice(1);
    const filename = metadata.getFilename(extension);
    const newFilepath = path.join(path.dirname(this.sourceFilepath), filename);
    if (newFilepath === this.sourceFilepath) {
      Logger.debug("renameFromMetadata - no new filepath", this.sourceFilepath);
      return;
    }
    this.newFilepath = newFilepath;
  }
  async removeDrm() {
    if (!this.sourceFilepath.endsWith(".epub")) {
      Logger.error("removeDrm - not an epub", this.sourceFilepath);
      return;
    }
    const tmpFilepath = this.getTmpFilepath();
    const drmType = detectDrm(tmpFilepath);
    if (drmType === "unencrypted") {
      Logger.debug("removeDrm - no drm", this.sourceFilepath);
      return;
    }
    if (drmType === "adobe") {
      const outFilepath = tmp.tmpNameSync({ postfix: ".epub" });
      if (!this.adobeKeyFilepath) {
        Logger.error("removeDrm - no adobe key", this.sourceFilepath);
        return;
      }
      removeAdobeDrm(tmpFilepath, outFilepath, this.adobeKeyFilepath);
      fs.renameSync(outFilepath, tmpFilepath);
      this.newFilepath = tmpFilepath;
    }
  }
  async convertPdf() {
    if (!this.sourceFilepath.endsWith(".pdf")) {
      Logger.error("convertPdf - not a pdf", this.sourceFilepath);
      return;
    }
    const inFilepath = this.getTmpFilepath();
    const outFilepath = tmp.tmpNameSync({ postfix: ".pdf" });
    runK2PdfOpt(inFilepath, outFilepath);
    fs.renameSync(outFilepath, inFilepath);
    // indicates we've done some operation
    this.newFilepath = this.sourceFilepath;
  }
  save() {
    // there'll only be a newFilepath if we've done some operations
    if (this.newFilepath) {
      if (!this.tmpFilepath) {
        throw new Error("No tmpFilepath to save from");
      }
      if (this.dry) {
        Logger.info("copy tmp file to", this.newFilepath);
      } else {
        if (this.newFilepath === this.sourceFilepath) {
          const backupFilepath = getBackupFilepath(this.sourceFilepath);
          fs.renameSync(this.sourceFilepath, backupFilepath);
        }
        fs.copyFileSync(this.tmpFilepath, this.newFilepath);
      }
      this.newFilepath = undefined;
    }
    // there could be a tmpFilepath from just the metadata operation
    if (this.tmpFilepath) {
      fs.unlinkSync(this.tmpFilepath);
      this.tmpFilepath = undefined;
    }
  }
}
