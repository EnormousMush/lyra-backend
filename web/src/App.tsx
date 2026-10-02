import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useMe } from "./lib/hooks";
import Shell from "./components/Shell";
import Landing from "./pages/Landing";
import { Login, Signup } from "./pages/Auth";
import Library from "./pages/Library";
import Studio from "./pages/Studio";
import Gallery from "./pages/Gallery";
import Atlas from "./pages/Atlas";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

function RequireAuth() {
  const me = useMe();
  const loc = useLocation();
  if (me.isLoading) return <div className="min-h-screen" />;
  if (!me.data) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <Outlet />;
}

function GuestOnly() {
  const me = useMe();
  if (me.isLoading) return <div className="min-h-screen" />;
  if (me.data) return <Navigate to="/library" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route path="/library" element={<Library />} />
          <Route path="/t/:id" element={<Studio />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/atlas" element={<Atlas />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
