import fuzzy from "fuzzy";
import { makeAutoObservable } from "mobx";
import type DbStore from "./DbStore";

export default class BookListStore {
	private dbStore;
	searchQuery = "";

	constructor(dbStore: DbStore) {
		this.dbStore = dbStore;
		makeAutoObservable(this);
	}
	setSearchQuery(query: string) {
		this.searchQuery = query;
	}
	get pending() {
		return this.dbStore.pending;
	}
	get error() {
		return this.dbStore.error;
	}
	get data() {
		return this.dbStore.books;
	}
	get dbLoaded() {
		return !this.dbStore.pending && this.dbStore.data !== null;
	}
	get editApi() {
		return this.dbStore.meta?.edit_api;
	}

	get errors() {
		const data = this.dbStore.books;
		if (!data) {
			return [];
		}
		return data.filter((d) => d.error === true);
	}

	get books(): {
		title: string;
		filename: string;
		author: string;
		hash: string;
		messages: string[];
	}[] {
		const { searchQuery } = this;
		const data = this.dbStore.books;
		if (!data) {
			return [];
		}
		// TODO: handle errors - probably that means
		//   something else at the root?
		const books = data
			.filter((d) => d.error === false)
			.map(({ filename, metadata: { title, author }, hash, messages }) => ({
				title: title || "(unknown)",
				author: author || "(unknown)",
				filename,
				hash,
				messages: messages || [],
				score: 0,
			}));
		if (!searchQuery) {
			return books;
		}
		for (const book of books) {
			for (const key of ["title", "author"] as const) {
				const match = fuzzy.match(searchQuery, book[key], {
					pre: "<b>",
					post: "</b>",
				});
				if (match) {
					book.score = match.score;
					book[key] = match.rendered;
				}
			}
		}
		return books.sort((a, b) => b.score - a.score);
	}
	async load() {
		this.dbStore.load();
	}
}
