import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout } from "@/components/layout/Layout";
import Monitor from "@/pages/Monitor";
import CampaignDetail from "@/pages/CampaignDetail";
import AnaliseMensal from "@/pages/AnaliseMensal";
import Historico from "@/pages/Historico";
import VPP from "@/pages/VPP";
import Previsao from "@/pages/Previsao";
import Watchlist from "@/pages/Watchlist";
import Status from "@/pages/Status";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 300_000,
      retry: 2,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Sonner />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Monitor />} />
            <Route path="/campanha/:id" element={<CampaignDetail />} />
            <Route path="/analise-mensal" element={<AnaliseMensal />} />
            <Route path="/historico" element={<Historico />} />
            <Route path="/vpp" element={<VPP />} />
            <Route path="/previsao" element={<Previsao />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/status" element={<Status />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
