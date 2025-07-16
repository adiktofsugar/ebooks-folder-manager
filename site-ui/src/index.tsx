import { createRoot } from "react-dom/client";
import App from "./App";
import "./global.css";
import DbStore from "./stores/DbStore";

// biome-ignore lint/style/noNonNullAssertion: <explanation>
const el = document.getElementById("root")!;
createRoot(el).render(<App />);
