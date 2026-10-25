import { Link, useNavigate } from "react-router-dom";
import { clearSession, getSession } from "../lib/auth";

export default function Layout({ children }) {
  const session = getSession();
  const navigate = useNavigate();

  function logout() {
    clearSession();
    navigate("/login");
  }

  return (
    <>
      <header>
        <Link to="/" style={{ fontWeight: 700 }}>
          Academic Certificate Verification
        </Link>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/verify">Verify Certificate</Link>
          <Link to="/student">Student</Link>
          {session?.role === "admin" && <Link to="/admin">Admin</Link>}
          {session?.role === "issuer" && <Link to="/issuer">Issuer</Link>}
          {session ? (
            <button onClick={logout}>Logout</button>
          ) : (
            <Link to="/login">Login</Link>
          )}
        </nav>
      </header>
      <main>{children}</main>
    </>
  );
}
