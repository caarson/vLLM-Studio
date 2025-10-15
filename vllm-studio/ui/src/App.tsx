import React, { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Plus, Triangle } from "lucide-react";

import {
  Model,
  SettingsGroup,
  addModel,
  fetchSettings,
  listModels,
  restartModel,
  routeModel,
  setManagerToken,
  updateSettings,
} from "@/lib/api";
import { AddModelDialog } from "@/components/AddModelDialog";
import { ModelCard } from "@/components/ModelCard";
import { ModelSettingsDrawer } from "@/components/ModelSettingsDrawer";
import { ChatDrawer } from "@/components/ChatDrawer";

function useManagerToken() {
  const [token, setToken] = useState<string>(() => window.localStorage.getItem("managerToken") ?? "");
  useEffect(() => {
    setManagerToken(token);
    window.localStorage.setItem("managerToken", token);
  }, [token]);
  return [token, setToken] as const;
}

export default function App() {
  const queryClient = useQueryClient();
  const [token, setToken] = useManagerToken();
  const [addOpen, setAddOpen] = useState(false);
  const [settingsModel, setSettingsModel] = useState<Model | null>(null);
  const [chatModel, setChatModel] = useState<Model | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const modelsQuery = useQuery<Model[]>({
    queryKey: ["models"],
    queryFn: listModels,
    refetchInterval: 4000,
  });

  const activeModel = useMemo(() => modelsQuery.data?.find((model: Model) => model.active), [modelsQuery.data]);

  const addModelMutation = useMutation({
    mutationFn: addModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
  });

  const settingsQuery = useQuery<SettingsGroup[]>({
    queryKey: ["settings", settingsModel?.name],
    queryFn: () => fetchSettings(settingsModel?.name ?? ""),
    enabled: Boolean(settingsModel?.name),
  });

  const saveSettingsMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (!settingsModel) return;
      await updateSettings(settingsModel.name, values);
      await restartModel(settingsModel.name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      if (settingsModel) {
        queryClient.invalidateQueries({ queryKey: ["progress", settingsModel.name] });
      }
    },
  });

  const [healthPulse, setHealthPulse] = useState("");
  const routeMutation = useMutation({
    mutationFn: (name: string) => routeModel(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
    },
  });
  useEffect(() => {
    if (!activeModel) {
      setHealthPulse("inactive");
      return;
    }
    if (activeModel.status === "running") {
      setHealthPulse("ok");
    } else if (activeModel.status === "starting") {
      setHealthPulse("starting");
    } else {
      setHealthPulse("error");
    }
  }, [activeModel?.status]);

  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col gap-8 px-12 py-12">
        <header className="flex flex-col gap-6 rounded-3xl border border-line-subtle bg-bg-card/80 p-8 shadow-panel">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-semibold uppercase tracking-[0.1em]">vLLM Studio</h1>
              <p className="mt-2 text-sm text-text-secondary">
                Manage multi-model vLLM fleets with live telemetry, monochrome clarity, and instant routing.
              </p>
            </div>
            <button
              onClick={() => setAddOpen(true)}
              className="flex items-center gap-3 rounded-full border border-white px-5 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111]"
            >
              <Plus className="h-4 w-4" strokeWidth={1.4} /> Add Model
            </button>
          </div>
          <div className="grid grid-cols-[1fr_auto_auto] items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase tracking-[0.3em] text-text-muted">Active Model</span>
              <select
                value={activeModel?.name ?? ""}
                onChange={(event) => {
                  const selected = modelsQuery.data?.find((model: Model) => model.name === event.target.value);
                  if (selected) {
                    routeMutation.mutate(selected.name);
                    setChatModel(selected);
                    setChatOpen(false);
                  }
                }}
                className="min-w-[220px] rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
              >
                <option value="">None</option>
                {modelsQuery.data?.map((model) => (
                  <option key={model.name} value={model.name} className="text-black">
                    {model.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-text-muted">
              <span>Health</span>
              {healthPulse === "ok" && <Check className="h-4 w-4" strokeWidth={1.4} />}
              {healthPulse === "starting" && <LoaderCircle className="h-4 w-4 animate-spin" strokeWidth={1.4} />}
              {healthPulse === "error" && <Triangle className="h-4 w-4" strokeWidth={1.4} />}
              {healthPulse === "inactive" && <span className="text-text-muted">N/A</span>}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase tracking-[0.3em] text-text-muted">Manager Token</span>
              <input
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                className="w-64 rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
                placeholder="••••••••"
              />
            </div>
          </div>
        </header>

        <main className="flex flex-1 flex-col gap-8 pb-10">
          {modelsQuery.isLoading ? (
            <div className="flex h-64 items-center justify-center rounded-3xl border border-line-subtle bg-bg-card/60 shadow-panel">
              <LoaderCircle className="h-6 w-6 animate-spin" strokeWidth={1.4} />
              <span className="ml-3 text-sm uppercase tracking-[0.3em] text-text-secondary">Loading catalog…</span>
            </div>
          ) : modelsQuery.data && modelsQuery.data.length > 0 ? (
            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              {modelsQuery.data.map((model) => (
                <ModelCard
                  key={model.name}
                  model={model}
                  onOpenSettings={setSettingsModel}
                  onOpenChat={(selected) => {
                    setChatModel(selected);
                    setChatOpen(true);
                  }}
                />
              ))}
            </section>
          ) : (
            <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-3xl border border-line-subtle bg-bg-card/60 text-center text-sm text-text-secondary shadow-panel">
              <p>No models registered yet.</p>
              <button
                className="rounded-full border border-white px-4 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111]"
                onClick={() => setAddOpen(true)}
              >
                Add your first model
              </button>
            </div>
          )}
        </main>
      </div>

      <AddModelDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onSubmit={async (payload) => {
          await addModelMutation.mutateAsync(payload);
        }}
      />

      <ModelSettingsDrawer
        open={Boolean(settingsModel)}
        onOpenChange={(open) => {
          if (!open) setSettingsModel(null);
        }}
        model={settingsModel}
        settings={settingsQuery.data}
        onSave={async (values) => {
          await saveSettingsMutation.mutateAsync(values);
          setSettingsModel(null);
        }}
        saving={saveSettingsMutation.isPending}
      />

      <ChatDrawer
        open={chatOpen}
        onOpenChange={(open) => setChatOpen(open)}
        modelName={chatModel?.name ?? activeModel?.name}
      />
    </div>
  );
}
