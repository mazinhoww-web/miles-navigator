const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const APIFY_API_TOKEN = Deno.env.get('APIFY_API_TOKEN');
    if (!APIFY_API_TOKEN) {
      return new Response(
        JSON.stringify({ success: false, error: 'APIFY_API_TOKEN not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const { action, actorId, input, runId, datasetId } = await req.json();

    let url: string;
    let method = 'GET';
    let body: string | undefined;

    switch (action) {
      case 'run': {
        // Start an actor run
        url = `https://api.apify.com/v2/acts/${actorId}/runs?token=${APIFY_API_TOKEN}`;
        method = 'POST';
        body = JSON.stringify(input ?? {});
        break;
      }
      case 'run-sync': {
        // Run actor and wait for results (up to 300s)
        url = `https://api.apify.com/v2/acts/${actorId}/run-sync-get-dataset-items?token=${APIFY_API_TOKEN}`;
        method = 'POST';
        body = JSON.stringify(input ?? {});
        break;
      }
      case 'status': {
        // Check run status
        url = `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_API_TOKEN}`;
        break;
      }
      case 'dataset': {
        // Get dataset items
        url = `https://api.apify.com/v2/datasets/${datasetId}/items?token=${APIFY_API_TOKEN}`;
        break;
      }
      case 'run-dataset': {
        // Get dataset from a specific run
        url = `https://api.apify.com/v2/actor-runs/${runId}/dataset/items?token=${APIFY_API_TOKEN}`;
        break;
      }
      default:
        return new Response(
          JSON.stringify({ success: false, error: `Unknown action: ${action}` }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
    }

    console.log(`Apify proxy: ${action} → ${method} ${url.replace(APIFY_API_TOKEN, '***')}`);

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      ...(body ? { body } : {}),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('Apify API error:', data);
      return new Response(
        JSON.stringify({ success: false, error: data.error?.message ?? `Apify request failed (${response.status})`, details: data }),
        { status: response.status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Apify proxy error:', error);
    const msg = error instanceof Error ? error.message : 'Unknown error';
    return new Response(
      JSON.stringify({ success: false, error: msg }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
