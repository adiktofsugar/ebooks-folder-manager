import {
	type ReactNode,
	createContext,
	useContext,
	useEffect,
	useState,
} from "react";

interface ThemeContextType {
	isDark: boolean;
	toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [isDark, setIsDark] = useState(() => {
		const saved = localStorage.getItem("theme");
		if (saved !== null) {
			return saved === "dark";
		}
		return window.matchMedia("(prefers-color-scheme: dark)").matches;
	});

	useEffect(() => {
		const root = document.documentElement;
		if (isDark) {
			root.classList.add("dark");
		} else {
			root.classList.remove("dark");
		}
		localStorage.setItem("theme", isDark ? "dark" : "light");
	}, [isDark]);

	useEffect(() => {
		const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
		const handleChange = (e: MediaQueryListEvent) => {
			const saved = localStorage.getItem("theme");
			if (saved === null) {
				setIsDark(e.matches);
			}
		};
		mediaQuery.addEventListener("change", handleChange);
		return () => mediaQuery.removeEventListener("change", handleChange);
	}, []);

	const toggleTheme = () => setIsDark(!isDark);

	return (
		<ThemeContext.Provider value={{ isDark, toggleTheme }}>
			{children}
		</ThemeContext.Provider>
	);
}

export function useTheme() {
	const context = useContext(ThemeContext);
	if (!context) {
		throw new Error("useTheme must be used within a ThemeProvider");
	}
	return context;
}
