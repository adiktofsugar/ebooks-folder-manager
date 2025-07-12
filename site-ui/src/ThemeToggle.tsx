import styles from "./ThemeToggle.module.css";
import { useTheme } from "./contexts/ThemeContext";

export default function ThemeToggle() {
	const { isDark, toggleTheme } = useTheme();

	return (
		<button
			type="button"
			onClick={toggleTheme}
			className={styles.toggle}
			aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
		>
			{isDark ? "☀️" : "🌙"}
		</button>
	);
}
