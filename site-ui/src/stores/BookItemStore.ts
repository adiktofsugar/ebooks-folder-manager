import { makeAutoObservable } from "mobx";
import type { BookResult } from "../interfaces";

export default class BookItemStore {
	title: string;
	author: string;
	filename: string;
	hash: string;
	messages: string[];
	original_filepath: string;

	constructor(book: BookResult) {
		this.title = book.metadata?.title || "(unknown)";
		this.author = book.metadata?.author || "(unknown)";
		this.filename = book.filename;
		this.hash = book.hash;
		this.messages = book.messages || [];
		this.original_filepath = book.original_filepath;
		makeAutoObservable(this);
	}
}
