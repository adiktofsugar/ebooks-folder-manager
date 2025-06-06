import { makeAutoObservable, when } from "mobx";
import fuzzy from 'fuzzy'
import SummaryStore from "./SummaryStore";
import BookDetailStore from "./BookDetailStore";

export default class BookListStore {
    private summaryStore = new SummaryStore();
    private bookDetailStores: BookDetailStore[] = [];
    searchQuery: string = '';

    constructor() {
        makeAutoObservable(this);
    }
    setSearchQuery(query: string) {
        this.searchQuery = query;
    }
    get pending() {
        return this.summaryStore.pending;
    }
    get error() {
        return this.summaryStore.error;
    }
    get files() {
        return this.summaryStore.data ? this.summaryStore.data.files : null;
    }
    get count() {
        return this.summaryStore.count;
    }
    get summaryLoaded() {
        return this.summaryStore.data !== null;
    }
    get booksLoadProgress() {
        if (!this.summaryLoaded) return 0;
        const total = this.bookDetailStores.length
        const loaded = this.bookDetailStores.filter(store => store.loaded).length;
        if (total === 0) return 1; // If there are no books, consider it fully loaded
        return loaded / total;
    }
    get booksLoaded() {
        return this.booksLoadProgress === 1;
    }
    get books(): { title: string, file: string, author: string }[] {
        if (!this.booksLoaded) {
            return [];
        }
        if (!this.searchQuery) {
            return this.bookDetailStores.map(book => ({
                title: book.title || '',
                file: book.filename!,
                author: book.author || '',
            }));
        }
        const titles = this.bookDetailStores.map(book => book.title || '');
        const results = fuzzy.filter(this.searchQuery, titles, {
            pre: '<b>',
            post: '</b>',
        });
        return results.map(result => {
            const { index, string } = result;
            const book = this.bookDetailStores[index];
            return { title: string, file: book.filename!, author: book.author || '' };
        });

    }
    async load() {
        this.summaryStore.load();
        when(() => this.summaryLoaded, () => this.files!.forEach(file => {
            const bookDetailStore = new BookDetailStore(file);
            this.bookDetailStores.push(bookDetailStore);
            bookDetailStore.load();
        }));
    }
}