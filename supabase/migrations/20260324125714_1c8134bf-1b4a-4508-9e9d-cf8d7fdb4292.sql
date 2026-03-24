-- Table to store Apify Actor configurations for each scraping source
CREATE TABLE public.apify_actors (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  source_name TEXT NOT NULL UNIQUE,
  actor_id TEXT NOT NULL DEFAULT '',
  display_name TEXT NOT NULL DEFAULT '',
  description TEXT DEFAULT '',
  is_enabled BOOLEAN NOT NULL DEFAULT true,
  schedule_minutes INTEGER NOT NULL DEFAULT 60,
  last_run_id TEXT,
  last_run_status TEXT,
  last_run_at TIMESTAMPTZ,
  last_dataset_id TEXT,
  last_items_found INTEGER DEFAULT 0,
  last_new_items INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.apify_actors ENABLE ROW LEVEL SECURITY;

-- Public access (internal tool, no auth)
CREATE POLICY "Anyone can read actors" ON public.apify_actors FOR SELECT USING (true);
CREATE POLICY "Anyone can insert actors" ON public.apify_actors FOR INSERT WITH CHECK (true);
CREATE POLICY "Anyone can update actors" ON public.apify_actors FOR UPDATE USING (true);
CREATE POLICY "Anyone can delete actors" ON public.apify_actors FOR DELETE USING (true);

-- Timestamp trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_apify_actors_updated_at
  BEFORE UPDATE ON public.apify_actors
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Seed the 14 default sources
INSERT INTO public.apify_actors (source_name, display_name, description) VALUES
  ('passageirodeprimeira', 'Passageiro de Primeira', 'Blog WordPress — promoções e análises de milhas'),
  ('melhoresdestinos', 'Melhores Destinos', 'Blog WordPress — alertas de promoções aéreas'),
  ('mestredasmilhas', 'Mestre das Milhas', 'Blog WordPress — dicas de milhas e pontos'),
  ('pontospravoar', 'Pontos pra Voar', 'Blog WordPress — promoções de transferência'),
  ('smiles', 'Smiles', 'Programa de fidelidade GOL — promoções diretas'),
  ('latampass', 'LATAM Pass', 'Programa de fidelidade LATAM — bônus de transferência'),
  ('azul', 'TudoAzul', 'Programa de fidelidade Azul — promoções e clube'),
  ('livelo', 'Livelo', 'Programa de pontos — transferências bonificadas'),
  ('esfera', 'Esfera', 'Programa Santander — campanhas de bônus'),
  ('itau_iupp', 'Itaú iupp', 'Programa Itaú — ofertas de transferência'),
  ('nubank', 'Nubank', 'Nubank Rewards — promoções de pontos'),
  ('c6', 'C6 Bank', 'C6 Átomos — campanhas de conversão'),
  ('inter', 'Inter', 'Inter Loop — transferências bonificadas'),
  ('sicoob', 'Sicoob', 'Sicoob Pontos — promoções esporádicas');