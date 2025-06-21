import { makeAutoObservable, runInAction } from "mobx";
import yaml from "yaml";
import type { DbResponse } from "../interfaces";

export default class DbStore {
	data: DbResponse | null = null;
	error: string | null = null;
	pending = false;
	constructor() {
		makeAutoObservable(this);
	}
	get count() {
		return this.data ? this.data.length : null;
	}
	async load() {
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
