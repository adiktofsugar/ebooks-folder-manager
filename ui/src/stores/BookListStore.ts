import { makeAutoObservable } from "mobx";
import fuzzy from 'fuzzy'
import DbStore from "./DbStore";

export default class BookListStore {
    private dbStore = new DbStore();
    searchQuery: string = '';

    constructor() {
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
        return this.dbStore.data ? this.dbStore.data : null;
    }
    get count() {
        return this.dbStore.count;
    }
    get dbLoaded() {
        return this.dbStore.data !== null;
    }

    get books(): { title: string, filename: string, author: string }[] {
        if (!this.data) {
            return [];
        }
        if (!this.searchQuery) {
            return this.data.map(({ filename, metadata: { title, author } }) => ({
                title: title || '(unknown)',
                filename,
                author: author || '(unknown)',
            }));
        }
        const titles = this.data.map(book => book.metadata.title || '');
        const results = fuzzy.filter(this.searchQuery, titles, {
            pre: '<b>',
            post: '</b>',
        });
        return results.map(result => {
            const { filename, metadata: { author } } = this.data![result.index];
            return { title: result.string, filename, author: author || '(unknown)' };
        });

    }
    async load() {
        this.dbStore.load();
    }
}