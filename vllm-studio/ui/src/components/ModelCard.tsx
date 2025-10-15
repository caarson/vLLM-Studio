import React, { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, ClipboardList, Play, Square, Wand2 } from "lucide-react";

import {
  Model,
  ProgressSnapshot,
  fetchProgress,
  routeModel,
  startModel,
  stopModel,
} from "@/lib/api";
import { MonoProgress } from "./MonoProgress";
import { StatusChip } from "./StatusChip";

interface Props {
  model: Model;
  onOpenSettings: (model: Model) => void;
  onOpenChat: (model: Model) => void;
}

function formatBytes(value: number): string {
  if (value <= 0) return "0";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let current = value;
  while (current >= 1024 && idx < units.length - 1) {
    current /= 1024;
    idx += 1;
  }
  return `${current.toFixed(2)} ${units[idx]}`;
}

function formatSeconds(totalSeconds: number | null): string {
  if (totalSeconds === null || totalSeconds <= 0) {
    return "--:--";
  }
  const hours = Math.floor(totalSeconds / 3600)
    .toString()
    .padStart(2, "0");
  const minutes = Math.floor((totalSeconds % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

export function ModelCard({ model, onOpenSettings, onOpenChat }: Props) {
  const queryClient = useQueryClient();
  const [logsOpen, setLogsOpen] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const progressQuery = useQuery<ProgressSnapshot>({
    queryKey: ["progress", model.name],
    queryFn: () => fetchProgress(model.name),
    refetchInterval: 2500,
    enabled: model.status !== "stopped",
  });

  const startMutation = useMutation({
    mutationFn: () => startModel(model.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["progress", model.name] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => stopModel(model.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["progress", model.name] });
    },
  });

  const routeMutation = useMutation({
    mutationFn: () => routeModel(model.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
  });

  useEffect(() => {
    if (!logsOpen) {
      ws?.close();
      setWs(null);
      return;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/api/logs/stream/${model.name}`);
    setWs(socket);
    socket.onmessage = (event) => {
      setLogs((prev: string[]) => [...prev.slice(-200), String(event.data)]);
    };
    socket.onerror = () => socket.close();
    return () => {
      socket.close();
    };
  }, [logsOpen, model.name]);

  const progress = progressQuery.data;
  const pct = useMemo(() => {
    if (!progress || progress.bytes_total === 0) return 0;
    return Math.min(100, (progress.bytes_downloaded / progress.bytes_total) * 100);
  }, [progress]);

  return (
    <section className="flex flex-col gap-4 rounded-3xl border border-line-subtle bg-bg-card/80 shadow-panel p-6">
      <header className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold uppercase tracking-[0.08em] text-white">{model.name}</h2>
          <p className="text-sm text-text-secondary">{model.repo}</p>
        </div>
        <StatusChip status={model.status} />
      </header>
      <div className="flex flex-col gap-4">
        <div>
          <MonoProgress value={pct} />
          <p className="mt-2 text-xs font-mono text-text-secondary">
            {(progress?.phase ?? "idle").toUpperCase()} · {pct.toFixed(0)}% ·
            {" "}
            {progress ? `${(progress.network_mbps_avg ?? 0).toFixed(2)} MB/s` : "--"} · ETA {formatSeconds(progress?.eta_seconds ?? null)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-2xl border border-line-subtle bg-bg-surface/80 p-4">
            <p className="uppercase text-xs tracking-[0.28em] text-text-muted">Disk</p>
            <p className="mt-1 text-text-primary text-lg">
              Required {(progress?.disk_needed_gb ?? 0).toFixed(1)} GB
            </p>
            <p className="text-xs text-text-secondary">Free {(progress?.disk_free_gb ?? 0).toFixed(1)} GB</p>
          </div>
          <div className="rounded-2xl border border-line-subtle bg-bg-surface/80 p-4">
            <p className="uppercase text-xs tracking-[0.28em] text-text-muted">VRAM</p>
            <p className="mt-1 text-text-primary text-lg">Est. {(progress?.vram_needed_gb ?? 0).toFixed(1)} GB</p>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-xs text-text-secondary">Free {(progress?.vram_free_gb ?? 0).toFixed(1)} GB</span>
              <span className="inline-flex items-center gap-1 rounded-full border border-white/60 px-2 py-0.5 text-[10px] uppercase tracking-[0.3em]">
                {progress?.vram_fit ? "FITS" : "TIGHT"}
              </span>
            </div>
          </div>
        </div>
      </div>
      <footer className="flex items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            className="px-4 py-2 border border-white/70 rounded-full text-white uppercase tracking-[0.3em] text-xs hover:bg-[#111] disabled:opacity-40"
            onClick={() => startMutation.mutate()}
            disabled={model.status === "running" || startMutation.isPending}
          >
            <Play className="inline-block w-4 h-4 mr-2" strokeWidth={1.4} /> Start
          </button>
          <button
            className="px-4 py-2 border border-white/70 rounded-full text-white uppercase tracking-[0.3em] text-xs hover:bg-[#111] disabled:opacity-40"
            onClick={() => stopMutation.mutate()}
            disabled={model.status === "stopped" || stopMutation.isPending}
          >
            <Square className="inline-block w-4 h-4 mr-2" strokeWidth={1.4} /> Stop
          </button>
          <button
            className="px-4 py-2 border border-white/70 rounded-full text-white uppercase tracking-[0.3em] text-xs hover:bg-[#111] disabled:opacity-40"
            onClick={() => routeMutation.mutate()}
            disabled={!model.port || routeMutation.isPending}
          >
            <Wand2 className="inline-block w-4 h-4 mr-2" strokeWidth={1.4} /> Use
          </button>
        </div>
        <div className="flex gap-2">
          <button
            className="px-4 py-2 border border-white/50 rounded-full text-xs uppercase tracking-[0.3em] hover:bg-[#111]"
            onClick={() => onOpenSettings(model)}
          >
            <ClipboardList className="inline-block w-4 h-4 mr-2" strokeWidth={1.4} /> Settings
          </button>
          <button
            className="px-4 py-2 border border-white/50 rounded-full text-xs uppercase tracking-[0.3em] hover:bg-[#111]"
            onClick={() => onOpenChat(model)}
          >
            Chat
          </button>
        </div>
      </footer>
      <div>
        <button
          className="flex w-full items-center justify-between rounded-2xl border border-line-subtle bg-bg-surface/80 px-4 py-2 text-sm text-text-secondary hover:bg-[#111]"
          onClick={() => setLogsOpen((prev) => !prev)}
        >
          <span>Logs</span>
          {logsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {logsOpen && (
          <pre className="mt-3 h-48 overflow-y-auto rounded-2xl border border-line-subtle bg-[#0d0d0d] p-3 text-xs text-text-muted">
{logs.length === 0 ? "Awaiting logs..." : logs.join("\n")}
          </pre>
        )}
      </div>
    </section>
  );
}
