import { Outlet, type RouteObject } from "react-router-dom";

import { App } from "../App";
import { CableSizingPage } from "../pages/CableSizingPage";
import { ChangePasswordPage } from "../pages/ChangePasswordPage";
import { FaultStudyPage } from "../pages/FaultStudyPage";
import { LoadStudyPage } from "../pages/LoadStudyPage";
import { LoginPage } from "../pages/LoginPage";
import { ProjectsPage } from "../pages/ProjectsPage";
import { TransformerSizingPage } from "../pages/TransformerSizingPage";
import { UsersPage } from "../pages/UsersPage";
import { AppShell } from "./AppShell";
import { AuthProvider } from "./AuthProvider";
import { ProjectProvider } from "./ProjectProvider";
import {
  CHANGE_PASSWORD_PATH,
  LOGIN_PATH,
  PROJECTS_PATH,
  RequireAuth,
  SignedOutOnly,
  USERS_PATH,
} from "./routeGuards";

// The route table, kept apart from createBrowserRouter so tests can run it in a memory router.
//
// Every route sits under the AuthProvider, and the ProjectProvider sits inside it so the
// chosen project follows the session. Only the sign-in page is open; the shell and with it
// every module page is behind RequireAuth. A new page added under the shell is guarded
// without any further step.
export const routes: RouteObject[] = [
  {
    element: (
      <AuthProvider>
        <ProjectProvider>
          <Outlet />
        </ProjectProvider>
      </AuthProvider>
    ),
    children: [
      {
        path: LOGIN_PATH,
        element: (
          <SignedOutOnly>
            <LoginPage />
          </SignedOutOnly>
        ),
      },
      {
        path: CHANGE_PASSWORD_PATH,
        element: (
          <RequireAuth allowPasswordChangePending>
            <ChangePasswordPage />
          </RequireAuth>
        ),
      },
      {
        // Layout route: the shell renders navigation and footer around every page via <Outlet />.
        path: "/",
        element: (
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        ),
        children: [
          { index: true, element: <App /> },
          { path: "load-demand", element: <LoadStudyPage /> },
          { path: "transformer-sizing", element: <TransformerSizingPage /> },
          { path: "fault-study", element: <FaultStudyPage /> },
          { path: "cable-sizing", element: <CableSizingPage /> },
          // Every signed-in member may read the project configuration; the server decides
          // who may write, and the page hides the actions a role cannot use.
          { path: PROJECTS_PATH.slice(1), element: <ProjectsPage /> },
          // Owner only: the page says so to anybody else, and the server refuses them (403).
          { path: USERS_PATH.slice(1), element: <UsersPage /> },
        ],
      },
    ],
  },
];
