import { useCallback, useEffect, useState } from "react";
import { usePlaidLink } from "react-plaid-link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PlaidLinkButton({ onLinked }: { onLinked: () => void }) {
  const { token } = useAuth();
  const [linkToken, setLinkToken] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api<{ link_token: string }>("/api/plaid/link-token", { method: "POST", token })
      .then((r) => setLinkToken(r.link_token))
      .catch(() => setLinkToken(null));
  }, [token]);

  const onSuccess = useCallback(
    async (publicToken: string, metadata: { institution: { name?: string; institution_id?: string } | null }) => {
      await api("/api/plaid/exchange", {
        method: "POST",
        token,
        body: {
          public_token: publicToken,
          institution_id: metadata.institution?.institution_id ?? null,
          institution_name: metadata.institution?.name ?? null,
        },
      });
      onLinked();
    },
    [token, onLinked],
  );

  const { open, ready } = usePlaidLink({ token: linkToken, onSuccess });

  return (
    <button
      disabled={!ready || !linkToken}
      onClick={() => open()}
      className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
    >
      Link a bank
    </button>
  );
}
