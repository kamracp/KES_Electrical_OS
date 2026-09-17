import { createBrowserRouter } from "react-router-dom";

import { App } from "../App";
import { CableSizingPage } from "../pages/CableSizingPage";
import { FaultStudyPage } from "../pages/FaultStudyPage";
import { AppShell } from "./AppShell";

// Layout route: the shell renders navigation and footer around every page via <Outlet />.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <App /> },
      { path: "fault-study", element: <FaultStudyPage /> },
      { path: "cable-sizing", element: <CableSizingPage /> },
    ],
  },
]);
