import { supabase } from '@/integrations/supabase/client';

type ApifyResponse<T = any> = {
  success: boolean;
  error?: string;
  data?: T;
};

export const apifyApi = {
  /** Run an actor and wait for results (sync, up to 300s) */
  async runSync<T = any>(actorId: string, input?: Record<string, any>): Promise<ApifyResponse<T>> {
    const { data, error } = await supabase.functions.invoke('apify-proxy', {
      body: { action: 'run-sync', actorId, input },
    });
    if (error) return { success: false, error: error.message };
    return data;
  },

  /** Start an actor run (async) */
  async run(actorId: string, input?: Record<string, any>): Promise<ApifyResponse> {
    const { data, error } = await supabase.functions.invoke('apify-proxy', {
      body: { action: 'run', actorId, input },
    });
    if (error) return { success: false, error: error.message };
    return data;
  },

  /** Check run status */
  async getRunStatus(runId: string): Promise<ApifyResponse> {
    const { data, error } = await supabase.functions.invoke('apify-proxy', {
      body: { action: 'status', runId },
    });
    if (error) return { success: false, error: error.message };
    return data;
  },

  /** Get dataset items */
  async getDataset<T = any>(datasetId: string): Promise<ApifyResponse<T>> {
    const { data, error } = await supabase.functions.invoke('apify-proxy', {
      body: { action: 'dataset', datasetId },
    });
    if (error) return { success: false, error: error.message };
    return data;
  },

  /** Get dataset items from a specific run */
  async getRunDataset<T = any>(runId: string): Promise<ApifyResponse<T>> {
    const { data, error } = await supabase.functions.invoke('apify-proxy', {
      body: { action: 'run-dataset', runId },
    });
    if (error) return { success: false, error: error.message };
    return data;
  },
};
