import axios, { AxiosRequestConfig, AxiosResponse } from "axios";

const API_BASE = import.meta.env.VITE_API_BASE ?? window.location.origin;

let token: string | undefined;

export function setManagerToken(value: string) {
  token = value.trim() || undefined;
}

const client = axios.create({
  baseURL: API_BASE,
});

client.interceptors.request.use((config: AxiosRequestConfig) => {
  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }
  return config;
});

export type ModelStatus = "running" | "starting" | "stopped" | "error";

export interface Model {
  name: string;
  repo: string;
  revision?: string | null;
  default_port: number;
  default_gpu: number;
  flags: Record<string, unknown>;
  status: ModelStatus;
  port?: number | null;
  gpu_index?: number | null;
  container_id?: string | null;
  health?: string | null;
  active?: boolean;
}

export interface ProgressFile {
  path: string;
  size: number;
  downloaded: number;
  complete: boolean;
}

export interface ProgressSnapshot {
  phase: "resolving" | "downloading" | "loading" | "ready" | "error";
  bytes_total: number;
  bytes_downloaded: number;
  network_mbps_avg: number;
  eta_seconds: number | null;
  disk_needed_gb: number;
  disk_free_gb: number;
  vram_needed_gb: number;
  vram_free_gb: number;
  vram_fit: boolean;
  files: ProgressFile[];
}

export interface SettingsField {
  key: string;
  type: string;
  value: unknown;
  default: unknown;
  description: string;
  choices?: string[] | null;
}

export interface SettingsGroup {
  group: string;
  fields: SettingsField[];
}

export function listModels() {
  return client.get<Model[]>("/api/models").then((res: AxiosResponse<Model[]>) => res.data);
}

export function addModel(payload: {
  name: string;
  repo: string;
  revision?: string | null;
  default_port?: number;
  default_gpu?: number;
  flags?: Record<string, unknown>;
}) {
  return client.post("/api/models", payload).then((res: AxiosResponse) => res.data);
}

export function startModel(name: string) {
  return client.post("/api/start", { name }).then((res: AxiosResponse) => res.data);
}

export function stopModel(name: string) {
  return client.post("/api/stop", { name }).then((res: AxiosResponse) => res.data);
}

export function routeModel(name: string) {
  return client.post("/api/route", { name }).then((res: AxiosResponse) => res.data);
}

export function fetchProgress(name: string) {
  return client
    .get<ProgressSnapshot>(`/api/progress/${name}`)
    .then((res: AxiosResponse<ProgressSnapshot>) => res.data);
}

export function fetchSettings(name: string) {
  return client
    .get<SettingsGroup[]>(`/api/settings/${name}`)
    .then((res: AxiosResponse<SettingsGroup[]>) => res.data);
}

export function updateSettings(name: string, values: Record<string, unknown>) {
  return client.put(`/api/settings/${name}`, { values }).then((res: AxiosResponse) => res.data);
}

export function restartModel(name: string) {
  return client.post("/api/restart", { name }).then((res: AxiosResponse) => res.data);
}
