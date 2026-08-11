import axios from "axios";

const BASE_URL = "http://localhost:8000/api";

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("classpulse_token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  first_name: string;
  crn: string;
  course: string;
  semester: number;
  section: string;
}

export interface LoginResponse {
  token: string;
  role: "student" | "teacher";
  username: string;
}

export async function registerStudent(payload: RegisterPayload) {
  const { data } = await api.post("/student/register/", payload);
  return data;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/student/login/", { username, password });
  localStorage.setItem("classpulse_token", data.token);
  localStorage.setItem("classpulse_role", data.role);
  return data;
}

export async function getStudentProfile() {
  const { data } = await api.get("/student/profile/");
  return data;
}

export function logout() {
  localStorage.removeItem("classpulse_token");
  localStorage.removeItem("classpulse_role");
}
