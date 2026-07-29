import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import "./app/tokens.css";
import "./app/theme.css";
import "./app/terminal.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
