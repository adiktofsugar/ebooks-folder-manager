export default class BookMetadata {
  title;
  creators;
  dateOfPublication;
  identifiers;
  primaryLanguage;
  isK2pdfoptVersion;
  constructor({
    title,
    creators,
    dateOfPublication,
    identifiers,
    primaryLanguage,
    isK2pdfoptVersion,
  }: {
    title: string;
    creators: string[];
    dateOfPublication: Date | null;
    identifiers: { scheme?: string; id: string }[];
    primaryLanguage: string;
    isK2pdfoptVersion: boolean;
  }) {
    this.title = title;
    this.creators = creators;
    this.dateOfPublication = dateOfPublication;
    this.identifiers = identifiers;
    this.primaryLanguage = primaryLanguage;
    this.isK2pdfoptVersion = isK2pdfoptVersion;
  }
  getFilename(extension: string) {
    const { title, creators } = this;
    const author = creators
      ? Array.isArray(creators)
        ? creators[0]
        : creators
      : "Unknown";
    return `${author} - ${title}.${extension}`;
  }
}
