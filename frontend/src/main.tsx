import React from "react";
import ReactDOM from "react-dom/client";
import { AuthScreen } from "./screens/AuthScreen";

import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AuthScreen />
  </React.StrictMode>,
);

