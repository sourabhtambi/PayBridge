import type { ReactNode } from "react";
import { NavBar } from "./NavBar";
import { RoleSwitcher } from "./RoleSwitcher";

export function AppShell({ children }: { children?: ReactNode }) {
  return (
    <>
      <a className="skip" href="#main">Skip to main content</a>
      <header className="appbar">
        <div className="brand">PayBridge</div>
        <RoleSwitcher />
      </header>
      <NavBar />
      <main id="main">{children}</main>
    </>
  );
}
