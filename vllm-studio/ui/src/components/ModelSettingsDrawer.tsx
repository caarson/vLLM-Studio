import * as Dialog from "@radix-ui/react-dialog";
import * as Accordion from "@radix-ui/react-accordion";
import React, { useEffect, useMemo, useState } from "react";

import { Model, SettingsGroup } from "@/lib/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  model: Model | null;
  settings: SettingsGroup[] | undefined;
  onSave: (values: Record<string, unknown>) => Promise<void>;
  saving: boolean;
}

function fieldInput(field: SettingsGroup["fields"][number], value: unknown, onChange: (next: unknown) => void) {
  const baseClass = "w-full rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white";
  switch (field.type) { 
    case "integer":
    case "number":
      return (
        <input
          type="number"
          className={baseClass}
          value={((value as number | string | undefined) ?? "") as string | number}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(field.type === "integer" ? parseInt(event.target.value, 10) : parseFloat(event.target.value))}
        />
      );
    case "boolean":
      return (
        <label className="inline-flex items-center gap-3 text-sm text-text-secondary">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border border-line-subtle bg-[#0f0f0f] text-white focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
            checked={Boolean(value)}
            onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.checked)}
          />
          {field.description}
        </label>
      );
    case "list":
      return (
        <input
          type="text"
          className={baseClass}
          value={Array.isArray(value) ? (value as unknown[]).join(", ") : ""}
          placeholder="comma separated"
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value.split(",").map((item) => item.trim()).filter(Boolean))}
        />
      );
    case "object":
      return (
        <textarea
          className={`${baseClass} min-h-[120px] font-mono`}
          value={value ? JSON.stringify(value, null, 2) : "{}"}
          onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => {
            try {
              onChange(JSON.parse(event.target.value));
            } catch {
              onChange(event.target.value);
            }
          }}
        />
      );
    default:
      return (
        <input
          type="text"
          className={baseClass}
          value={(value as string | undefined) ?? ""}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
        />
      );
  }
}

export function ModelSettingsDrawer({ open, onOpenChange, model, settings, onSave, saving }: Props) {
  const initialValues = useMemo(() => {
    if (!settings) return {};
    const all: Record<string, unknown> = {};
    for (const group of settings) {
      for (const field of group.fields) {
        all[field.key] = field.value ?? field.default;
      }
    }
    return all;
  }, [settings]);

  const [values, setValues] = useState<Record<string, unknown>>(initialValues);

  useEffect(() => {
    setValues(initialValues);
  }, [initialValues]);

  if (!model) {
    return null;
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/80" />
        <Dialog.Content className="fixed inset-y-0 right-0 w-[760px] overflow-y-auto border-l border-line-subtle bg-bg-card/95 p-10 shadow-panel focus:outline-none">
          <Dialog.Title className="text-2xl font-semibold uppercase tracking-[0.2em] text-white">
            {model.name} · Settings
          </Dialog.Title>
          <div className="mt-8 grid grid-cols-[220px_1fr] gap-10">
            <nav className="sticky top-10 flex flex-col gap-3 text-xs uppercase tracking-[0.3em] text-text-muted">
              {settings?.map((group) => (
                <a key={group.group} href={`#${group.group.replace(/\s+/g, "-").toLowerCase()}`} className="hover:text-white">
                  {group.group}
                </a>
              ))}
            </nav>
            <Accordion.Root type="multiple" className="space-y-6">
              {settings?.map((group) => (
                <Accordion.Item key={group.group} value={group.group} id={group.group.replace(/\s+/g, "-").toLowerCase()}>
                  <Accordion.Trigger className="flex w-full items-center justify-between rounded-2xl border border-line-subtle bg-bg-surface/80 px-4 py-3 text-left text-sm text-text-secondary hover:bg-[#111]">
                    <span>{group.group}</span>
                  </Accordion.Trigger>
                  <Accordion.Content className="mt-4 space-y-4 border border-line-subtle bg-bg-surface/60 p-4 rounded-2xl">
                    {group.fields.map((field) => (
                      <div key={field.key} className="grid grid-cols-[160px_1fr] items-start gap-6">
                        <div>
                          <p className="text-xs uppercase tracking-[0.3em] text-text-muted">{field.key}</p>
                          <p className="mt-1 text-xs text-text-secondary">{field.description}</p>
                        </div>
                        <div>
                          {fieldInput(field, values[field.key], (next) => setValues((prev) => ({ ...prev, [field.key]: next })))}
                        </div>
                      </div>
                    ))}
                  </Accordion.Content>
                </Accordion.Item>
              ))}
            </Accordion.Root>
          </div>
          <div className="mt-10 flex justify-end gap-4">
            <Dialog.Close asChild>
              <button className="rounded-full border border-white/50 px-4 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111]">Close</button>
            </Dialog.Close>
            <button
              className="rounded-full border border-white px-5 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111] disabled:opacity-40"
              onClick={() => onSave(values)}
              disabled={saving}
            >
              Save & Restart
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
