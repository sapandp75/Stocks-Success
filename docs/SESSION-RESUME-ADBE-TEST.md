# Session Resume: ADBE Deep Dive Smoke Test

## Context
Deep Dive Frontend V2 was just built (2026-04-10). 22 new components, revised spec, all adversarial review findings addressed. Build passes. Need to verify the full stack works end-to-end with real data for Adobe (ADBE).

## What To Do

Run a complete ADBE deep dive test **in terminal only** — no browser. Exercise every layer: backend API, bridge CLI, MCP tools, and verify the frontend build serves correctly.

### Step 1: Start the backend
```bash
cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system"
./start.sh &
sleep 3
```

### Step 2: Test the API endpoint (raw data)
```bash
curl -s http://localhost:8000/api/deep-dive/ADBE | python3 -m json.tool | head -80
```
Verify: fundamentals, gates, data_quality, technicals, financial_history fields present.

### Step 3: Test V2 backend services
```bash
# These should be in the deep-dive response. Check for new V2 fields:
curl -s http://localhost:8000/api/deep-dive/ADBE | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k in ['quarterly', 'growth_metrics', 'forward_estimates', 'external_targets', 'fund_flow', 'staleness_days', 'gates', 'reverse_dcf', 'forward_dcf', 'sensitivity_matrix', 'peers', 'analyst', 'insider_activity', 'institutional']:
    v = d.get(k)
    status = 'PRESENT' if v else 'MISSING'
    print(f'  {k}: {status}')
print(f'\nAI analysis: {\"PRESENT\" if d.get(\"ai_analysis\") else \"NOT YET RUN\"}')
"
```

### Step 4: Run AI analysis via bridge
```bash
cd "/Users/sbakshi/Documents/Stocks Success"
python bridge/deep_dive_worker.py ADBE --post
```
This calls Gemini to generate the 8-section analysis and POSTs to the API. Verify all 8 sections appear in output.

### Step 5: Verify AI analysis landed
```bash
curl -s http://localhost:8000/api/deep-dive/ADBE | python3 -c "
import json, sys
d = json.load(sys.stdin)
ai = d.get('ai_analysis', {})
sections = ['first_impression', 'bear_case_stock', 'bear_case_business', 'bull_case_rebuttal', 'bull_case_upside', 'valuation', 'whole_picture', 'self_review', 'verdict', 'conviction', 'entry_grid', 'exit_playbook', 'moat_structured', 'opportunities', 'threats', 'scenarios']
for s in sections:
    v = ai.get(s)
    if v:
        preview = str(v)[:80].replace(chr(10), ' ')
        print(f'  {s}: ✓ {preview}...')
    else:
        print(f'  {s}: ✗ MISSING')
"
```

### Step 6: Test MCP tools (TradingView)
Use the TradingView MCP tools to fetch live data for ADBE:
- `mcp__tradingview-screener__combined_analysis` with symbol ADBE
- `mcp__tradingview-screener__multi_timeframe_analysis` with symbol ADBE
- `mcp__tradingview-screener__market_sentiment`

Print key outputs from each.

### Step 7: Test regime endpoint
```bash
curl -s http://localhost:8000/api/regime | python3 -m json.tool
```

### Step 8: Test screener
```bash
curl -s http://localhost:8000/api/screener/latest | python3 -c "
import json, sys
d = json.load(sys.stdin)
b1 = [s['ticker'] for s in d.get('b1_candidates', [])]
b2 = [s['ticker'] for s in d.get('b2_candidates', [])]
print(f'B1 candidates ({len(b1)}): {b1[:10]}')
print(f'B2 candidates ({len(b2)}): {b2[:10]}')
adbe = 'ADBE' in b1 or 'ADBE' in b2
print(f'ADBE in results: {adbe}')
"
```

### Step 9: Test frontend build
```bash
cd "/Users/sbakshi/Documents/Stocks Success/frontend"
npx vite build 2>&1 | tail -5
```
Verify: build succeeds, no errors, bundle includes recharts.

### Step 10: Verify frontend is served
```bash
curl -s http://localhost:8000/ | head -5
```
Should return HTML with React app.

## Success Criteria
- [ ] API returns ADBE fundamentals + gates + all V2 fields
- [ ] Bridge generates AI analysis for all 8 sections
- [ ] AI analysis persists and is retrievable via API
- [ ] MCP tools return TradingView data
- [ ] Regime endpoint returns current market state
- [ ] Screener returns B1/B2 candidates
- [ ] Frontend builds without errors
- [ ] Frontend is served at localhost:8000

## If Something Fails
- Backend won't start: check `start.sh` exists, check port 8000 not in use (`lsof -i :8000`)
- Bridge fails: check Gemini API key in env (`echo $GEMINI_API_KEY`)
- V2 fields missing: backend services may not be registered in the deep-dive router — check `backend/routers/deep_dive.py`
- MCP tools fail: check `.mcp.json` config
- Frontend build fails: run `cd frontend && npm install` first
