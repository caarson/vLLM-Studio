import * as Dialog from "@radix-ui/react-dialog";
import React, { useState } from "react";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: { name: string; repo: string; revision?: string | null }) => Promise<void>;
}

export function AddModelDialog({ open, onOpenChange, onSubmit }: Props) {
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");
  const [revision, setRevision] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name || !repo) {
      setError("Name and repo are required");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await onSubmit({ name, repo, revision: revision || undefined });
      setName("");
      setRepo("");
      setRevision("");
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add model");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/80" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-line-subtle bg-bg-card/95 p-8 shadow-panel focus:outline-none">
          <Dialog.Title className="text-xl font-semibold uppercase tracking-[0.2em] text-white">Add Model</Dialog.Title>
          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block text-xs uppercase tracking-[0.3em] text-text-muted">
              Name
              <input
                className="mt-2 w-full rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
                value={name}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => setName(event.target.value)}
                required
              />
            </label>
            <label className="block text-xs uppercase tracking-[0.3em] text-text-muted">
              Hugging Face Repo
              <input
                className="mt-2 w-full rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
                value={repo}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => setRepo(event.target.value)}
                required
              />
            </label>
            <label className="block text-xs uppercase tracking-[0.3em] text-text-muted">
              Revision (optional)
              <input
                className="mt-2 w-full rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
                value={revision}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => setRevision(event.target.value)}
              />
            </label>
            {error && <p className="text-xs text-text-secondary">{error}</p>}
            <div className="flex justify-end gap-3 pt-4">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-full border border-white/50 px-4 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111]"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                className="rounded-full border border-white px-4 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111] disabled:opacity-40"
                disabled={pending}
              >
                Save
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
