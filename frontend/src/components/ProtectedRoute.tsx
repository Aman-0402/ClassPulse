import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getToken } from "../utils/session";

export default function ProtectedRoute() {
  const token = getToken();
  const location = useLocation();
  return token ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }} />;
}
