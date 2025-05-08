import { createClient } from 'npm:@supabase/supabase-js@2.39.7';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? ''
    );

    // Fetch assets from database
    const { data: assets, error: assetsError } = await supabaseClient
      .from('assets')
      .select('*');

    if (assetsError) throw assetsError;

    // Fetch market data for each asset
    const marketData = await Promise.all(
      assets.map(async (asset) => {
        const response = await fetch(
          `https://finnhub.io/api/v1/quote?symbol=${asset.ticker}&token=${Deno.env.get('FINNHUB_API_KEY')}`
        );
        const data = await response.json();
        return {
          asset_id: asset.id,
          ticker: asset.ticker,
          current_price: data.c,
          previous_close: data.pc,
          high: data.h,
          low: data.l,
          timestamp: new Date().toISOString(),
        };
      })
    );

    return new Response(
      JSON.stringify(marketData),
      {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    );
  }
});