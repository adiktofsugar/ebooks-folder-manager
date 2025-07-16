export interface Metadata {
	title?: string;
	author?: string;
}

export interface ErrorResult {
	error: true;
	error_message: string;
	messages: string[];
	original_filepath: string;
	temp_directory: string;
}
export interface BookResult {
	error: false;
	metadata: Metadata;
	filename: string;
	hash: string;
	messages: string[];
	original_filepath: string;
}
export type Result = ErrorResult | BookResult;

export interface DbMeta {
	edit_api?: string;
}

export interface DbResponse {
	meta: DbMeta;
	books: Result[];
}
