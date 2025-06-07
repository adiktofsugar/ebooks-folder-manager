export interface Metadata {
    title?: string;
    author?: string;
}

export interface Result {
    filename: string;
    metadata: Metadata
}

export type DbResponse = Result[];