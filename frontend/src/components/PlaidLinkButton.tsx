import { useCallback, useEffect, useState } from "react";
import { usePlaidLink } from "react-plaid-link";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSyncMutation } from "@/lib/sync";

type Phase = "idle" | "exchanging" | "syncing";

export default function PlaidLinkButton({ onLinked }: { onLinked: () => void }) {
  const { token } = useAuth();
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  const sync = useSyncMutation();

  useEffect(() => {
    if (!token) return;
    api<{ link_token: string }>("/api/plaid/link-token", { method: "POST", token })
      .then((r) => setLinkToken(r.link_token))
      .catch(() => setLinkToken(null));
  }, [token]);

  const onSuccess = useCallback(
    async (
      publicToken: string,
      metadata: { institution: { name?: string; institution_id?: string } | null },
    ) => {
      setError(null);
      setPhase("exchanging");
      try {
        await api("/api/plaid/exchange", {
          method: "POST",
          token,
          body: {
            public_token: publicToken,
            institution_id: metadata.institution?.institution_id ?? null,
            institution_name: metadata.institution?.name ?? null,
          },
        });
      } catch (e) {
        setPhase("idle");
        setError(humanizeError(e, "Couldn't link bank"));
        return;
      }

      setPhase("syncing");
      try {
        await sync.mutateAsync();
      } catch (e) {
        setError(humanizeError(e, "Linked, but initial sync failed — try Refresh"));
      } finally {
        setPhase("idle");
        onLinked();
      }
    },
    [token, onLinked, sync],
  );

  const { open, ready } = usePlaidLink({ token: linkToken, onSuccess });

  const busy = phase !== "idle";
  const label =
    phase === "exchanging"
      ? "Linking…"
      : phase === "syncing"
        ? "Syncing transactions…"
        : "Link a bank";

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        disabled={!ready || !linkToken || busy}
        onClick={() => open()}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {label}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

function humanizeError(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    const body = e.body as { detail?: string } | null;
    return body?.detail ? `${fallback}: ${body.detail}` : fallback;
  }
  return fallback;
}
