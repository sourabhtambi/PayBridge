import { navItemsFor } from "../../service/navigation";
import { usePathname } from "../hooks/usePathname";
import { useSession } from "../state/SessionContext";

export function NavBar() {
  const { session } = useSession();
  const pathname = usePathname();
  return (
    <nav className="nav" aria-label="Primary">
      <ul>
        {navItemsFor(session.role).map((item) => (
          <li key={item.route}>
            <a href={item.route} aria-current={pathname === item.route ? "page" : undefined}>
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
