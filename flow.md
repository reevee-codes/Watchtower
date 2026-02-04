# Flow działania programu - API Monitoring Decision Agent

## Wprowadzenie

Program to agent monitorujący zdrowie API, który działa w pętli: **Obserwuj → Decyduj → Działaj**. Agent sprawdza API, zbiera dane o jego stanie i podejmuje decyzje czy kontynuować monitorowanie, zatrzymać się, ponowić próbę lub wysłać alert.

---

## Główny flow działania

### 1. Punkt wejścia (`main.py`)

```python
agent = Agent(goal="API healthy")
await agent.run()
```

Tworzy agenta z celem (obecnie nieużywanym) i uruchamia główną pętlę.

### 2. Główna pętla (`agent/agent.py` - metoda `run()`)

```python
while True:
    await self.observe()           # Krok 1: Obserwacja
    decision_result = self.decide()  # Krok 2: Decyzja
    done = self.act(decision_result) # Krok 3: Akcja
    if done:
        break
```

Pętla działa aż do momentu, gdy agent zdecyduje się zatrzymać (`STOP`) lub wyśle alert (`ALERT`).

---

## Szczegółowy opis kroków

### Krok 1: OBSERWACJA (`observe()`)

**Co się dzieje:**
- Wywołuje `check_api()` z modułu `environment/http_env.py`
- `check_api()` losowo wybiera jeden z URL-i i wykonuje asynchroniczne żądanie HTTP
- Zwraca:
  - `status`: "OK", "ERROR" lub "TIMEOUT"
  - `latency_ms`: czas odpowiedzi w milisekundach

**Aktualizacja stanu:**
- Zwiększa licznik `steps` o 1 (numer iteracji pętli)
- Zwiększa odpowiedni licznik:
  - `ok_count++` jeśli status = "OK"
  - `error_count++` jeśli status = "ERROR"
  - `timeout_count++` jeśli status = "TIMEOUT"
- Zapisuje: `last_status`, `last_latency_ms`

### Krok 2: DECYZJA (`decide()`)

**Budowanie snapshotu stanu:**
```python
inp = {
    "ok_count": self.state.ok_count,
    "error_count": self.state.error_count,
    "timeout_count": self.state.timeout_count,
    "last_status": self.state.last_status,
    "latency_ms": self.state.last_latency_ms,
}
```

**Próba użycia LLM (`decision/llm_decision.py`):**
- Wysyła prompt do OpenAI z aktualnym stanem
- Oczekuje JSON z:
  - `decision`: "STOP", "CONTINUE", "RETRY", "ALERT"
  - `incident_type`: typ incydentu (np. "HEALTHY", "PERSISTENT_ERROR")
  - `confidence`: pewność decyzji (liczba)
- Waliduje odpowiedź

**Fallback do reguł (`decision/rules_decision.py`):**
Jeśli LLM:
- Rzuci wyjątek
- Zwróci nieprawidłowy format
- Nie będzie dostępny

**Reguły deterministyczne:**
- `ok_count >= 3` → **STOP** (HEALTHY) - API działa stabilnie
- `error_count >= 3` → **ALERT** (PERSISTENT_ERROR) - zbyt wiele błędów
- `timeout_count >= 3` → **RETRY** (TIMEOUT_INSTABILITY) - problemy z timeoutami
- W przeciwnym razie → **CONTINUE** (RULE_BASED) - kontynuuj monitorowanie

**Zapis telemetrii:**
- `last_decision`, `last_incident_type`, `last_confidence`, `last_source` (LLM lub RULES)

### Krok 3: AKCJA (`act()`)

**Logowanie:**
Wypisuje telemetrię:
```
step=1 status=OK ok=1 err=0 to=0 decision=CONTINUE incident=HEALTHY source=LLM conf=0.95 latency_ms=150
```

**Wykonanie akcji:**
- **ALERT** lub **PERSISTENT_ERROR** → wywołuje `send_alert()` i kończy pętlę (`return True`)
- **STOP** → kończy pętlę (`return True`)
- **RETRY** / **CONTINUE** → kontynuuje pętlę (`return False`)

**Powtarzanie:**
Pętla trwa aż do:
- Agent zdecyduje **STOP** (np. 3+ sukcesy)
- Zostanie wywołany **ALERT** (np. 3+ błędy)

---

## Architektura

```
main.py
  └── Agent (agent/agent.py)
       ├── AgentState (agent/state.py) - przechowuje stan
       │   ├── steps: int - licznik iteracji
       │   ├── ok_count, error_count, timeout_count - liczniki
       │   └── last_status, last_latency_ms - ostatnie wartości
       │
       ├── observe() → environment/http_env.py
       │   └── check_api() - wykonuje HTTP request
       │
       ├── decide() → decision/llm_decision.py (LLM)
       │              └── fallback → decision/rules_decision.py (reguły)
       │
       └── act() - wykonuje decyzję i loguje
```

---

## Odpowiedzi na często zadawane pytania

### 1. Na co wpływa parametr `goal`?

**Odpowiedź:** Na nic. Jest przechowywany w `self.goal`, ale nie jest używany:
- ❌ Nie jest przekazywany do LLM
- ❌ Nie jest używany w decyzjach
- ❌ Nie jest używany w regułach
- ❌ Nie jest używany w logice agenta

To **martwy kod** - parametr istnieje, ale nie ma wpływu na działanie programu. Prawdopodobnie został zaplanowany do użycia, ale nie został zaimplementowany.

### 2. Co to jest `steps`?

**Odpowiedź:** `steps` to **licznik iteracji pętli głównej**:
- Zwiększa się o 1 przy każdym wywołaniu `observe()`
- Używany do:
  - Logowania: `f"step={self.state.steps} ..."`
  - Alertów: `f"... after {self.state.steps} steps"`

To po prostu numer kroku w monitorowaniu (1, 2, 3...).

### 3. Po co używać LLM? Czy tylko dla CV?

**Odpowiedź:** W obecnej formie wygląda na to, że głównie dla CV/demonstracji. Powody:

**Dlaczego może być niepotrzebne:**
- ✅ Reguły są bardzo proste i deterministyczne - łatwo je zakodować bez LLM
- ✅ LLM nie dostaje `goal`, więc nie może go używać w kontekście
- ✅ Prompt jest bardzo prosty - można to zastąpić regułami
- ✅ Jest fallback do reguł, więc LLM jest opcjonalny

**Potencjalne korzyści z LLM (gdyby było lepiej zaimplementowane):**
- Bardziej elastyczne decyzje (np. uwzględnianie latencji)
- Lepsze rozpoznawanie wzorców (np. niestabilność)
- Możliwość rozszerzenia o więcej kontekstu

**Wniosek:** W obecnej formie LLM nie wnosi dużo ponad proste reguły, ale może być użyteczne przy rozbudowie systemu.

### 4. Co robi `CONTINUE`?

**Odpowiedź:** `CONTINUE` oznacza **"kontynuuj pętlę - nie kończ działania"**.

W `act()`:
```python
if result.decision == "STOP":
    return True  # kończy pętlę
    
# retry/continue = keep running
return False  # kontynuuje pętlę
```

**Różnica między `CONTINUE` a `RETRY`:**
- Oba zwracają `False` → pętla kontynuuje
- Różnica jest tylko **semantyczna** (w `incident_type` i logach)
- W praktyce działają tak samo - następna iteracja pętli

**Podsumowanie:** 
- `CONTINUE` = "monitoruj dalej, nic nie rób"
- `RETRY` = "monitoruj dalej, może problem się rozwiąże"

---

## Kluczowe cechy projektu

1. **Separacja odpowiedzialności:**
   - `environment/` - warstwa środowiska (HTTP requests)
   - `decision/` - warstwa decyzyjna (LLM + reguły)
   - `agent/` - logika agenta

2. **Fallback do reguł:**
   - Jeśli LLM nie działa, używa deterministycznych reguł
   - System zawsze działa, nawet bez API key

3. **Stan agenta:**
   - Agent śledzi historię (liczniki, ostatni status)
   - Stan jest aktualizowany przy każdej obserwacji

4. **Asynchroniczność:**
   - Używa `async/await` dla żądań HTTP
   - Nie blokuje wykonania podczas czekania na odpowiedź

---

## Typy decyzji

- **STOP** - zatrzymaj monitorowanie (API działa stabilnie)
- **CONTINUE** - kontynuuj monitorowanie (nic nie rób)
- **RETRY** - kontynuuj monitorowanie (może problem się rozwiąże)
- **ALERT** - wyślij alert i zatrzymaj (krytyczny problem)

## Typy incydentów

- **HEALTHY** - API działa poprawnie
- **TRANSIENT_ERROR** - przejściowy błąd
- **PERSISTENT_ERROR** - trwały błąd (wymaga alertu)
- **TIMEOUT_INSTABILITY** - problemy z timeoutami
- **UNKNOWN** - nieznany typ incydentu
- **RULE_BASED** - decyzja podjęta przez reguły

---

## Uruchomienie

```bash
python main.py
```

**Wymagania:**
- Zmienna środowiskowa `OPENAI_API_KEY` (opcjonalna - działa bez niej z regułami)
- Zainstalowane zależności z `requirements.txt`
