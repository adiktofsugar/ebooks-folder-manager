import { observer } from "mobx-react-lite";
import styles from "./ThemeToggle.module.css";
import type ThemeStore from "./stores/ThemeStore";

export default observer(function ThemeToggle({ store }: { store: ThemeStore }) {
	return (
		<button
			type="button"
			onClick={() => store.toggleTheme()}
			className={styles.toggle}
			aria-label={`Switch to ${store.dark ? "light" : "dark"} mode`}
		>
			{store.dark ? "☀️" : "🌙"}
		</button>
	);
});
