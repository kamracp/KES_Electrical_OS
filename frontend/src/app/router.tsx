import { createBrowserRouter } from "react-router-dom";

import { App } from "../App";
import { CableSizingPage } from "../pages/CableSizingPage";
import { FaultStudyPage } from "../pages/FaultStudyPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
  },
  {
    path: "/fault-study",
    element: <FaultStudyPage />,
  },
  {
    path: "/cable-sizing",
    element: <CableSizingPage />,
  },
]);
