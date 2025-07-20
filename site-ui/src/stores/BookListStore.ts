import fuzzy from "fuzzy";
import { makeAutoObservable } from "mobx";
import { createContext, useContext } from "react";
import type { BookMatchData } from "../interfaces";
import BookItemStore from "./BookItemStore";
import type DbStore from "./DbStore";

interface BookWithMatch {
	book: BookItemStore;
	matchData: BookMatchData;
}

export const BookListStoreContext = createContext<BookListStore | null>(null);
export function useBookListStore() {
	const store = useContext(BookListStoreContext);
	if (!store) throw new Error("No BookListStore in context");
	return store;
}
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

	get books(): BookItemStore[] {
		const data = this.dbStore.books;
		if (!data) {
			return [];
		}
		// TODO: handle errors - probably that means
		//   something else at the root?
		return data
			.filter((d) => d.error === false)
			.map((book) => new BookItemStore(book));
	}

	get booksSorted(): BookWithMatch[] {
		const { searchQuery, books } = this;

		const booksWithMatch = books.map((book) => {
			let score = 0;
			let titleHtml = book.title;
			let authorHtml = book.author;

			if (searchQuery) {
				const titleMatch = fuzzy.match(searchQuery, book.title, {
					pre: "<b>",
					post: "</b>",
				});
				if (titleMatch) {
					score = Math.max(score, titleMatch.score);
					titleHtml = titleMatch.rendered;
				}

				const authorMatch = fuzzy.match(searchQuery, book.author, {
					pre: "<b>",
					post: "</b>",
				});
				if (authorMatch) {
					score = Math.max(score, authorMatch.score);
					authorHtml = authorMatch.rendered;
				}
			}

			return {
				book,
				matchData: {
					score,
					titleHtml,
					authorHtml,
				},
			};
		});

		if (!searchQuery) {
			return booksWithMatch;
		}

		return booksWithMatch.sort((a, b) => b.matchData.score - a.matchData.score);
	}
	async load() {
		this.dbStore.load();
	}
}
