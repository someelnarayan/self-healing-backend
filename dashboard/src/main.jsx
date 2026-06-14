import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

import {
  ThemeProvider,
  createTheme,
} from "@mui/material/styles";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
  },
});

ReactDOM.createRoot(
  document.getElementById("root")
).render(
  <ThemeProvider theme={darkTheme}>
    <App />
  </ThemeProvider>
);