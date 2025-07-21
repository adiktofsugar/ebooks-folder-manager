import { makeAutoObservable, runInAction } from "mobx";
import yaml from "yaml";
import type { DbResponse } from "../interfaces";
import BookListStore from "./BookListStore";

export default class DbStore {
	data: DbResponse | null = null;
	error: string | null = null;
	pending = false;
	constructor() {
		makeAutoObservable(this);
	}
	get bookStore() {
		return this.data ? new BookListStore(this) : null;
	}
	get books() {
		return this.data?.books || null;
	}
	get meta() {
		return this.data?.meta || null;
	}
	async load() {
		if (this.data) {
			return;
		}
		this.pending = true;
		try {
			const response = await fetch(new URL("db.yaml", window.location.href));
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			const text = await response.text();
			runInAction(() => {
				this.data = yaml.parse(text);
				this.pending = false;
			});
		} catch (error) {
			runInAction(() => {
				this.error = error instanceof Error ? error.message : "Unknown error";
				this.pending = false;
			});
		}
	}
}
