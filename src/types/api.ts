export interface Campaign {
  id: number;
  title: string;
  source_name: string;
  source_url: string;
  promo_url: string;
  promo_type: 'transfer_bonus' | 'direct_purchase' | 'club_combo' | 'flash_sale' | 'club_signup' | 'other';
  origin_program: string | null;
  destination_program: string | null;
  reference_month: string;
  starts_at: string | null;
  ends_at: string | null;
  duration_days: number | null;
  is_flash: boolean;
  bonus_pct_base: number | null;
  bonus_pct_max: number | null;
  min_transfer: number | null;
  max_transfer: number | null;
  cpm_estimated: number | null;
  cpm_min: number | null;
  vpp_real_base: number | null;
  vpp_real_clube: number | null;
  vpp_real_elite: number | null;
  detected_at: string;
  published_at: string | null;
  confidence_score: number;
  extraction_method: 'regex' | 'llm';
  bonus_tiers: BonusTier[];
  loyalty_tiers: LoyaltyTier[];
  raw_text?: string;
}

export interface BonusTier {
  id: number;
  tier_name: string;
  bonus_pct: number;
  condition: string;
  requires_club: boolean;
  requires_card: boolean;
  vpp_real?: number;
  economy_per_k?: number;
  classification?: string;
}

export interface LoyaltyTier {
  id: number;
  min_months: number;
  bonus_pct_extra: number;
  label: string;
}

export interface MonthAnalysis {
  reference_month: string;
  total_campaigns: number;
  new_campaigns: number;
  best_bonus: number | null;
  min_cpm: number | null;
  flash_count: number;
  active_count: number;
  delta_campaigns: number;
  by_day: Array<{ day: string; max_bonus: number | null; count: number }>;
  by_program: Array<{ program: string; count: number }>;
  by_type: Array<{ promo_type: string; count: number }>;
}

export interface ScraperStatus {
  name: string;
  last_run: string | null;
  last_status: string;
  last_found: number;
  last_new: number;
  duration_s: number | null;
  bootstrap_complete: boolean;
  bootstrap_oldest: string | null;
  bootstrap_pages: number;
  bootstrap_campaigns: number;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  timestamp: string;
  total_campaigns: number;
  active_now: number;
  this_month: number;
  scrapers_ok: number;
  scrapers_error: number;
  scrapers: ScraperStatus[];
}

export interface WatchlistEntry {
  id: number;
  origin: string | null;
  destination: string | null;
  min_bonus_pct: number | null;
  notes: string | null;
  created_at: string;
}

export interface HistoryResponse {
  monthly_series: Array<{ month: string; bonus_avg: number | null; count: number }>;
  route_metrics?: {
    freq_per_month: number;
    avg_duration: number;
    avg_bonus: number;
    max_bonus: number;
    min_cpm: number;
    next_window_est: string | null;
  };
}

export interface SeasonalityData {
  programs: string[];
  grid: Array<{ program: string; months: number[] }>;
}

export interface InsightItem {
  text: string;
  metric: string;
  metric_value: string;
}

export interface PredictionRoute {
  origin: string;
  destination: string;
  probability_30d: number;
  bonus_range_low: number;
  bonus_range_high: number;
  urgency: 'imminent' | 'high' | 'monitor' | 'wait';
  evidence: string[];
}

export interface PredictionEvent {
  name: string;
  expected_date: string;
  days_remaining: number;
  programs: string[];
  description: string;
}

export interface VppCampaign {
  campaign_id: number;
  title: string;
  date: string;
  bonus_base: number;
  bonus_max: number;
  vpp_base: number;
  vpp_clube: number | null;
  vpp_elite: number | null;
  economy_per_k: number;
  classification: string;
  program: string;
}

export interface ActivePromosResponse {
  count: number;
  items: Campaign[];
}
