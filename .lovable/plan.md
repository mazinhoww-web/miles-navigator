

## Plano: Restaurar estrutura completa renomeando "LATAM Pass" para "Pass"

O problema: ao remover referências, a funcionalidade foi perdida (filtro "Pass" no Monitor, targets VPP, styling no ProgramPill, etc.). O plano restaura TUDO, apenas trocando o nome para "Pass".

---

### Alterações

**1. `src/pages/Monitor.tsx`** — Adicionar "Pass" de volta aos filtros
- Linha 15: `FILTER_PROGRAMS = ["Todos", "Smiles", "Azul", "Pass", "⚡ Flash"]`

**2. `src/pages/CampaignDetail.tsx`** — Restaurar VPP target para Pass
- Linha 19: `VPP_TARGETS = { smiles: 16, azul: 14, pass: 14 }`

**3. `src/pages/VPP.tsx`** — Restaurar Pass nos targets e opções
- Linha 18: `VPP_TARGETS = { Smiles: 16, "Azul Fidelidade": 14, Pass: 14 }`

**4. `src/components/ui/ProgramPill.tsx`** — Adicionar estilo para "Pass"
- Adicionar condição: `n.includes('pass') ? 'bg-purple-500/12 text-purple-400 border border-purple-500/20'`

**5. Migration SQL** — Criar nova migration para atualizar o seed data
- `UPDATE apify_actors SET source_name='pass', display_name='Pass', description='Programa de fidelidade — bônus de transferência' WHERE source_name='latampass';`

---

### Resultado
Todas as páginas voltam a funcionar com a estrutura original completa. O nome "Pass" substitui "LATAM Pass" em todos os pontos sem deixar rastro da marca original.

