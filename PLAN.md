# Implementation Plan — API Monitoring Decision Agent

Każda faza to oddzielna sesja robocza. Zacznij od góry, odhaczaj po kolei.

---

## Status

- [ ] Faza 0 — Code Review Fixes (poprawki przed dalszymi fazami)
- [x] Faza 1 — Structured Logging + SQLite
- [x] Faza 2 — Evaluation Framework
- [ ] Faza 3 — Chaos Engineering Module
- [ ] Faza 4 — FastAPI + Web Dashboard
- [ ] Faza 5 — Multi-model Comparison
- [ ] Faza 6 — GitHub Actions CI

---

## Faza 0 — Code Review Fixes

**Cel:** usunąć długi techniczne z review zanim dojdą kolejne fazy. Kolejność = priorytet.

### Critical
- [ ] **C1 — async LLM.** `decision/llm_decision.py`: `OpenAI` → `AsyncOpenAI`, `llm_decide` → `async def ... await`. `agent_async.py`: `decide()` → `async def`, wywołania LLM równolegle przez `asyncio.gather` po endpointach (wydzielić `_decide_one(r)`). W `run()`: `decisions = await self.decide(results)`.
- [ ] **C2 — walidacja enumów outputu LLM.** Walidować `decision` ∈ {RETRY,IGNORE,ALERT,ESCALATE}, `incident_type` ∈ {HEALTHY,TRANSIENT_ERROR,PERSISTENT_ERROR,TIMEOUT_INSTABILITY,UNKNOWN}, `confidence` ∈ [0,1]. Niepoprawny output → `ValueError` → fallback. (Pełna nowa wersja pliku w tej sesji.)

### High
- [ ] **H1 — wąski except.** `agent_async.py:66`: `except Exception` → `except (ValueError, openai.OpenAIError)`; zapisać `repr(exc)` do logu (pole `fallback_reason`).
- [ ] **H2 — singleton klienta.** Klient OpenAI na poziomie modułu, nie w `llm_decide`.
- [ ] **H3 — None content.** Jawne `if not raw: raise ValueError` przed `json.loads`.

### Medium / Low
- [ ] **M1** — usunąć `print(">>> LLM ... <<<")` z `llm_decision.py`.
- [ ] **M2** — `max_steps` do `config` zamiast `self.step >= 10` w `act()`.
- [ ] **M3** — policzyć `llm_cost_usd` z `response.usage` (albo usunąć kolumnę do Fazy 2).
- [ ] **M4** — jeden `httpx.AsyncClient` na życie agenta (reuse połączeń).
- [ ] **L2** — pierwszy test: `_fallback_decide` (czysta funkcja, 4 przypadki).

**Acceptance criteria:**
- [ ] `decide()` jest async i robi calle LLM równolegle (gather)
- [ ] Output LLM spoza enumów → fallback, nie trafia do DB
- [ ] Brak `print()` debugowych w `decision/`
- [ ] `_fallback_decide` ma test jednostkowy

---

## Faza 1 — Structured Logging + SQLite

**Cel:** każda decyzja zapisana jako JSON log i do bazy. Bez tego nie mamy danych do evalów.

**Pliki do stworzenia:**
- `observability/logger.py` — zapisuje każdy krok jako JSON do pliku `.jsonl`
- `observability/db.py` — SQLite, tabela `decisions`
- `observability/__init__.py`

**Pliki do modyfikacji:**
- `agent_async.py` — dodać wywołania loggera po każdej decyzji

**Schemat logu (jeden wiersz JSON per decyzja):**
```json
{
  "ts": "2026-06-14T10:23:01Z",
  "step": 3,
  "source": "llm",
  "last_status": "ERROR",
  "ok_count": 1,
  "error_count": 2,
  "timeout_count": 0,
  "latency_ms": 89.4,
  "llm_latency_ms": 342.1,
  "llm_cost_usd": 0.0012,
  "decision": "ALERT",
  "incident_type": "TRANSIENT_ERROR",
  "confidence": 0.87
}
```

**Schemat tabeli SQLite:**
```sql
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT,
  step INTEGER,
  source TEXT,           -- 'llm' | 'fallback'
  last_status TEXT,
  ok_count INTEGER,
  error_count INTEGER,
  timeout_count INTEGER,
  latency_ms REAL,
  llm_latency_ms REAL,
  llm_cost_usd REAL,
  decision TEXT,
  incident_type TEXT,
  confidence REAL
);
```

**Acceptance criteria:**
- [ ] Po uruchomieniu `main.py` powstaje plik `logs/decisions.jsonl`
- [ ] Po uruchomieniu `main.py` powstaje plik `data/decisions.db` z wypełnioną tabelą
- [ ] Każdy krok agenta ma wpis w obu miejscach
- [ ] Pole `source` poprawnie rozróżnia LLM od fallbacku

---

## Faza 2 — Evaluation Framework

**Cel:** porównać decyzje LLM vs reguły vs ground truth. Wyliczyć precision/recall. To jest Twój killer feature.

**Pliki do stworzenia:**
- `eval/ground_truth.py` — funkcja która na podstawie stanu zwraca "prawdziwą" decyzję
- `eval/metrics.py` — precision, recall, false positives, false negatives, accuracy
- `eval/report.py` — wypisuje raport po zakończeniu sesji agenta
- `eval/__init__.py`

**Pliki do modyfikacji:**
- `agent_async.py` — w każdym kroku wywołać też `rule_decide()` i `ground_truth()`, przekazać do eval
- `decision/llm_decision.py` — upewnić się że zwraca `source: 'llm'`

**Ground truth logic (prosta, deterministyczna):**
```
3x OK z rzędu       → STOP (healthy)
error_count >= 2    → ALERT
timeout_count >= 2  → ALERT
error_count >= 3    → ESCALATE
inaczej             → RETRY
```

**Przykładowy raport końcowy:**
```
=== EVALUATION REPORT ===
Total steps: 12
LLM decisions: 10 | Fallback decisions: 2

LLM vs Ground Truth:
  Accuracy:  83.3%
  Precision: 0.80
  Recall:    0.75
  FP: 2  FN: 1

LLM vs Rule-based:
  Agreement: 90%
  Disagreements: 1x LLM=ALERT, Rules=RETRY

Avg LLM latency: 287ms | Avg cost/decision: $0.0009
```

**Acceptance criteria:**
- [ ] Po zakończeniu sesji agenta wypisuje raport
- [ ] Raport zawiera porównanie LLM vs ground truth i LLM vs reguły
- [ ] Metryki precision/recall poprawnie wyliczone
- [ ] Raport zapisuje się też do pliku `reports/eval_YYYY-MM-DD_HH-MM.txt`

---

## Faza 3 — Chaos Engineering Module

**Cel:** wstrzykiwać kontrolowane awarie do środowiska i mierzyć jak agent reaguje. QA + AI = unikalna nisza.

**Pliki do stworzenia:**
- `chaos/scenarios.py` — definicje scenariuszy
- `chaos/injector.py` — wrapper na `check_api()` który wstrzykuje chaos
- `chaos/__init__.py`
- `chaos/README.md` — opis każdego scenariusza (ważne na CV)

**Scenariusze:**
```python
class ChaosScenario(Enum):
    NONE               = "none"             # normalny tryb
    FLAPPING_API       = "flapping"         # na przemian OK/ERROR co krok
    GRADUAL_DEGRADATION = "degradation"     # rosnące latencje: 100ms → 2000ms
    INTERMITTENT_TIMEOUT = "intermittent"   # 30% szans na TIMEOUT
    PERSISTENT_ERROR   = "persistent"       # stały ERROR przez N kroków, potem OK
    SPIKE              = "spike"            # jeden ERROR, reszta OK
```

**Pliki do modyfikacji:**
- `environment_async.py` — przepuścić przez `chaos/injector.py`
- `main.py` — dodać argument `--chaos <scenario>` (argparse)

**Uruchomienie:**
```bash
python main.py --chaos flapping
python main.py --chaos gradual_degradation
python main.py --chaos none
```

**Acceptance criteria:**
- [ ] Każdy scenariusz działa i produkuje przewidywalne wzorce statusów
- [ ] `--chaos none` daje identyczne zachowanie jak przed zmianą
- [ ] Eval report pokazuje wykrywalność awarii per scenariusz (czas do pierwszego ALERT)

---

## Faza 4 — FastAPI + Web Dashboard

**Cel:** zamiast `print()` — REST API i prosta strona z live statusem. Jeden screenshot = więcej niż 500 linii kodu.

**Pliki do stworzenia:**
- `api/app.py` — FastAPI aplikacja
- `api/routes/status.py` — endpoint `/status`
- `api/routes/history.py` — endpoint `/history`
- `api/routes/metrics.py` — endpoint `/metrics`
- `api/routes/trigger.py` — endpoint `POST /trigger`
- `api/__init__.py`
- `static/index.html` — prosta strona HTML (vanilla JS, bez frameworków)

**Endpointy:**
```
GET  /status       → { running, current_step, last_decision, last_status }
GET  /history?n=20 → lista ostatnich N decyzji z DB
GET  /metrics      → { accuracy, precision, recall, total_cost_usd, avg_latency }
POST /trigger      → ręczne uruchomienie jednego kroku agenta
GET  /             → serwuje static/index.html
```

**Dashboard (index.html) zawiera:**
- status badge: HEALTHY / ALERT / ESCALATE z kolorem
- tabelka ostatnich 10 decyzji (ts, decision, source, confidence)
- prosty wykres confidence w czasie (można użyć Chart.js z CDN)
- przycisk "Run Check Now" → POST /trigger

**Pliki do modyfikacji:**
- `main.py` — dodać `--mode api` który startuje FastAPI zamiast loop
- `agent_async.py` — agent musi działać jako singleton dostępny z API

**Uruchomienie:**
```bash
python main.py           # normalny tryb (loop)
python main.py --mode api  # tryb API na porcie 8000
```

**Acceptance criteria:**
- [ ] `GET /history` zwraca dane z SQLite
- [ ] `GET /metrics` zwraca poprawne metryki eval
- [ ] `POST /trigger` uruchamia jeden krok i zwraca wynik
- [ ] Strona HTML działa w przeglądarce i auto-odświeża się co 5s
- [ ] Screenshot strony wygląda "profesjonalnie" (można pokazać na CV)

---

## Faza 5 — Multi-model Comparison

**Cel:** ten sam scenariusz, różne modele, porównanie decyzji + kosztów.

**Pliki do stworzenia:**
- `eval/model_comparison.py` — uruchamia N modeli na tych samych danych, porównuje
- `reports/model_comparison_YYYY-MM-DD.md` — auto-generowany raport

**Modele do porównania:**
- `gpt-4o-mini` (tani, szybki)
- `gpt-4o` (drogi, dokładny)
- `gpt-3.5-turbo` (stary baseline)
- opcjonalnie: Claude przez Anthropic API (wymaga osobnego klucza)

**Pliki do modyfikacji:**
- `config/llm.yaml` — dodać sekcję `models:` z listą
- `decision/llm_decision.py` — przyjąć `model_name` jako parametr

**Przykładowy raport:**
```
=== MODEL COMPARISON — 2026-06-14 ===
Scenario: flapping (20 steps)

Model           | Accuracy | Avg Latency | Avg Cost/step | Agreements w/ GPT-4o
gpt-4o          |  91.7%   |  387ms      | $0.0041       | —
gpt-4o-mini     |  83.3%   |  112ms      | $0.0004       | 85%
gpt-3.5-turbo   |  75.0%   |  98ms       | $0.0002       | 78%
```

**Acceptance criteria:**
- [ ] `python main.py --compare-models` uruchamia pełne porównanie
- [ ] Raport zapisuje się do pliku
- [ ] Ten sam seed/scenariusz dla każdego modelu (reprodukowalność)

---

## Faza 6 — GitHub Actions CI

**Cel:** automatyczne testy przy każdym push. Zielona plakietka w README = sygnał jakości.

**Pliki do stworzenia:**
- `.github/workflows/test.yml`
- `requirements.txt` (jeśli jeszcze nie ma)
- Zaktualizowany `README.md` z plakietką CI

**Workflow:**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

**Testy do napisania (jeśli brakuje):**
- testy dla `eval/metrics.py` (precision/recall z hardkodowanymi danymi)
- testy dla `chaos/scenarios.py` (każdy scenariusz produkuje oczekiwany wzorzec)
- testy dla `decision/llm_decision.py` (mockując OpenAI)

**Acceptance criteria:**
- [ ] `pytest tests/ -v` przechodzi lokalnie
- [ ] Workflow uruchamia się na GitHub przy push
- [ ] README ma plakietkę `![Tests](https://github.com/.../.../actions/...)`
- [ ] Wszystkie testy przechodzą w CI

---

## Jak używać tego planu

1. Otwórz nową sesję Claude Code
2. Powiedz: *"Realizujemy Fazę X z PLAN.md"*
3. Claude przeczyta ten plik i będzie wiedział co robić
4. Po zakończeniu fazy zaktualizuj checkbox w tym pliku

---

## Zależności między fazami

```
Faza 1 (Logging/SQLite)
  ↓
Faza 2 (Eval) — wymaga danych z Fazy 1
  ↓
Faza 3 (Chaos) — wzbogaca dane do evalów
  ↓
Faza 4 (Dashboard) — czyta z SQLite i eval
  ↓
Faza 5 (Multi-model) — rozszerza eval o modele
  ↑
Faza 6 (CI) — można równolegle z dowolną fazą
```
