import { makeAutoObservable, runInAction } from "mobx";
import type { EditServerInfoResponse } from "../interfaces";

export default class EditApiInfoStore {
	data: EditServerInfoResponse | null = null;
	error: string | null = null;
	pending = false;
	baseUrl;
	constructor(baseUrl: string) {
		this.baseUrl = baseUrl;
		makeAutoObservable(this);
	}
	async load() {
		this.pending = true;
		this.error = null;
		try {
			const response = await fetch(`${this.baseUrl}/info`);
			if (!response.ok) {
				throw new Error(`Status: ${response.status}`);
			}
			const data = await response.json();
			runInAction(() => {
				this.data = data;
				this.pending = false;
			});
		} catch (e) {
			runInAction(() => {
				this.error = String(e);
				this.pending = false;
			});
		}
	}
}
