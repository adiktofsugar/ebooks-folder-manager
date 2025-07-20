import { makeAutoObservable, runInAction } from "mobx";
import yaml from "yaml";
import type { EditDbResponse } from "../interfaces";
import EditApiInfoStore from "./EditApiInfoStore";

export default class EditDbStore {
	data: EditDbResponse | null = null;
	error: string | null = null;
	pending = false;
	constructor() {
		makeAutoObservable(this);
	}
	get api() {
		if (!this.data) {
			return null;
		}
		return {
			info: new EditApiInfoStore(this.data.url),
		};
	}
	async load() {
		this.pending = true;
		try {
			const response = await fetch(
				new URL("edit-db.yaml", window.location.href),
			);
			if (response.status === 404) {
				runInAction(() => {
					this.data = null;
					this.pending = false;
				});
				return;
			}
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
