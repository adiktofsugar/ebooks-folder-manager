import { autorun, makeAutoObservable } from "mobx";

export default class ThemeStore {
	dark: boolean;
	constructor() {
		const saved = localStorage.getItem("theme");
		if (saved !== null) {
			this.dark = saved === "dark";
		} else {
			this.dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
		}
		makeAutoObservable(this);
		autorun(() => {
			localStorage.setItem("theme", this.dark ? "dark" : "light");
		});
	}
	toggleTheme() {
		this.dark = !this.dark;
	}
}
