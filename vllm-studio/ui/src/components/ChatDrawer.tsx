import * as Dialog from "@radix-ui/react-dialog";
import React, { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  modelName?: string;
}

export function ChatDrawer({ open, onOpenChange, modelName }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    const updated = [...messages, { role: "user", content: input.trim() }];
    setMessages(updated);
    setInput("");
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: modelName,
          messages: updated.map((message) => ({ role: message.role, content: message.content })),
          stream: false,
        }),
      });
      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`);
      }
      const json = await response.json();
      const assistant = json?.choices?.[0]?.message?.content ?? "(no response)";
  setMessages((prev: Message[]) => [...prev, { role: "assistant", content: assistant }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/80" />
        <Dialog.Content className="fixed inset-y-0 right-0 w-[520px] border-l border-line-subtle bg-bg-card/95 p-8 shadow-panel focus:outline-none">
          <Dialog.Title className="text-xl font-semibold uppercase tracking-[0.2em] text-white">
            Chat · {modelName ?? "No active"}
          </Dialog.Title>
          <div className="mt-6 flex h-full flex-col">
            <div className="flex-1 overflow-y-auto rounded-2xl border border-line-subtle bg-bg-surface/70 p-4 text-sm text-text-secondary">
              {messages.length === 0 ? (
                <p className="text-text-muted">Start a conversation to probe latency and quality.</p>
              ) : (
                <ul className="space-y-3">
                  {messages.map((message: Message, index: number) => (
                    <li key={`${message.role}-${index}`} className="rounded-2xl border border-line-subtle bg-[#0d0d0d] p-3">
                      <p className="text-xs uppercase tracking-[0.3em] text-text-muted">{message.role}</p>
                      <p className="mt-1 whitespace-pre-wrap text-text-primary">{message.content}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <form className="mt-4" onSubmit={handleSend}>
              <textarea
                className="h-32 w-full rounded-2xl border border-line-subtle bg-[#0f0f0f] px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-white"
                value={input}
                onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setInput(event.target.value)}
              />
              {error && <p className="mt-2 text-xs text-text-secondary">{error}</p>}
              <div className="mt-3 flex justify-end">
                <button
                  type="submit"
                  className="rounded-full border border-white px-5 py-2 text-xs uppercase tracking-[0.3em] hover:bg-[#111] disabled:opacity-40"
                  disabled={pending}
                >
                  Send
                </button>
              </div>
            </form>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
