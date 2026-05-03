/**
 * Sync hook + types shared between the Dashboard's Refresh button and the
 * PlaidLinkButton's post-exchange auto-sync.
 *
 * Both code paths invoke the same useMutation, so cache invalidation and
 * loading/error UI behave consistently.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export type SyncItemResult = {
  plaid_item_id: string;
  institution_name: string | null;
  accounts_upserted: number;
  transactions_added: number;
  transactions_modified: number;
  transactions_removed: number;
  last_synced_at: string;
  error: string | null;
};

export type SyncResponse = {
  items: SyncItemResult[];
  total_accounts_upserted: number;
  total_transactions_added: number;
  total_transactions_modified: number;
  total_transactions_removed: number;
};

export function useSyncMutation() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation<SyncResponse>({
    mutationFn: () =>
      api<SyncResponse>("/api/plaid/sync", { method: "POST", token }),
    onSuccess: () => {
      // refresh the dashboard's account list to reflect newly-synced data
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}
