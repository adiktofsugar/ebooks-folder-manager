import { makeAutoObservable, runInAction } from "mobx";
import yaml from 'yaml'
import { BookDetailResponse } from "../interfaces";

export default class BookDetailStore {
    private file: string;
    private data: BookDetailResponse | null = null;
    error: string | null = null;
    pending: boolean = false;
    constructor(file: string) {
        makeAutoObservable(this);
        this.file = file;
    }
    get title() {
        return this.data ? this.data.title : null;
    }
    get author() {
        return this.data ? this.data.author : null;
    }
    get filename() {
        return this.data ? this.data.filename : null;
    }
    get loaded() {
        return this.data !== null;
    }
    async load() {
        this.pending = true;
        try {
            const response = await fetch(new URL(this.file, window.location.href));
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const text = await response.text();
            runInAction(() => {
                this.data = yaml.parse(text);
                this.pending = false;
            })
        } catch (error) {
            runInAction(() => {
                this.error = error instanceof Error ? error.message : 'Unknown error';
                this.pending = false;
            });
        }
    }
}