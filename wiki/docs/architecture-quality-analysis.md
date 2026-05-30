# Architecture Quality Analysis

> Autore: analisi condotta su sessione Claude Code (2026-05-29)  
> Versione analizzata: 3.1.2

---

## Punti di forza

### Dual representation

Il problema di base — il pattern wiki di Karpathy scala male perché l'agente non può leggere 50 file per ogni query — è reale. Markdown + LanceDB come due viste sincronizzate della stessa conoscenza è la soluzione corretta. L'atomicità `.tmp → staging → promote` è un pattern crash-safe genuino.

### Pre-prompt injection

I sistemi alternativi richiedono che l'agente classifichi il messaggio come QUERY e invochi un tool. Se sbaglia la classificazione, non recupera il contesto. L'iniezione automatica prima di ogni prompt elimina questa dipendenza — il contesto arriva sempre, indipendentemente dall'intent classification.

### Ciclo knowledge coerente

`ingest → query → synthesize → promote → reflect` forma un loop chiuso logicamente consistente. La gerarchia tre layer (domain → distilled → identity) ha criteri di promozione chiari e asimmetria corretta: la conoscenza sale verso l'alto solo quando ha dimostrato utilità cross-domain.

---

## Tensioni di design e soluzioni proposte

### T1 — L'agente è il guardiano della consistenza

**Problema:** Il sistema dipende dall'agente che classifica correttamente gli intent e segue il protocollo di `wiki-core.md`. Non c'è enforcement — è fiducia pura in un LLM.

**Soluzioni:**

**A — Post-operation verification hook** *(bassa complessità)*  
Aggiungere a `wiki_context.py` un controllo euristico sull'ultimo turno: se il testo dell'agente contiene pattern di correzione comportamentale (`"sempre"`, `"mai"`, `"non farlo"`, `"stop doing"`) ma nessuna chiamata a `behavior-log` è stata fatta nella sessione corrente, iniettare un reminder nel prossimo `<wiki-context>`:

```
⚠️ MISSED BEHAVIOR_FEEDBACK? Last response contained correction signals
but no behavior-log was called. Run: wiki.py behavior-log --event "..."
```

**B — Intent classification log** *(media complessità)*  
Il plugin registra in `.wiki-intent-log.jsonl` ogni intent emesso dall'agente (già presente nel formato `[INTENT: X | ...]`). Un job periodico rileva AMBIGUOUS frequenti o BEHAVIOR_FEEDBACK mai seguiti da `behavior-log`. Superficie nel dashboard stats tab.

**C — Structured output enforcement** *(alta complessità)*  
Richiedere che ogni risposta dell'agente inizi con un JSON strutturato `{"intent": "...", "actions": [...]}` validabile lato plugin. Rifiuta risposte che non seguono il protocollo. Troppo invasivo per uso generale, ma valido in contesti controllati.

---

### T2 — L'auto-sintesi persiste errori di ragionamento

**Problema:** L'agente decide autonomamente quando il suo ragionamento è abbastanza buono da diventare conoscenza permanente. Un'inferenza sbagliata ma formulata con confidenza supera i criteri (≥2 fonti, >300 token, inferenza non-letterale) e viene recuperata nelle query successive come fatto.

**Soluzioni:**

**A — Staging area per sintesi** *(bassa complessità, raccomandata)*  
Le sintesi automatiche non vanno in `wiki/` ma in `wiki-works/<project>/synthesis-pending/`. Restano lì fino a conferma esplicita dell'utente o dell'agente in una sessione successiva. La pending area è visibile nel dashboard. La promozione da pending a wiki richiede un secondo ingest esplicito.

```
# Flusso attuale
synthesis → wiki/synthesis/slug.md  ← diretto, permanente

# Flusso proposto
synthesis → wiki-works/X/synthesis-pending/slug.md.pending
         → visibile nel dashboard tab "Review"
         → wiki/synthesis/slug.md  ← solo dopo conferma
```

**B — Confidence metadata** *(bassa complessità)*  
Ogni pagina scritta da auto-sintesi porta un frontmatter `confidence: low` e una `review_by` date (+30 giorni). `wiki.py lint` segnala pagine scadute come da rivedere. L'agente al momento della revisione può promuovere a `confidence: high` o eliminare.

```markdown
---
confidence: low
source: auto-synthesis
review_by: 2026-06-28
---
```

**C — Contradiction check pre-write** *(media complessità)*  
Prima di scrivere una pagina di sintesi, fare una query semantica e verificare che nessuna pagina esistente abbia similarità > 0.85 con contenuto opposto. Se trovata, non scrivere — segnalare il conflitto all'agente.

---

### T3 — Promozione misura frequenza, non qualità

**Problema:** "Citato in ≥3 query distinte" è una metrica di popolarità. Una pagina sbagliata ma spesso recuperata viene promossa. Il sistema può amplificare errori.

**Soluzioni:**

**A — Stability signal** *(bassa complessità)*  
Aggiungere ai criteri di promozione: la pagina non deve essere stata modificata dall'ultimo ingest. Una pagina che viene corretta spesso non è stabile — non merita promozione. Implementabile leggendo `git log` o confrontando il timestamp dell'ultimo embed con quello dell'ultimo write.

**B — Explicit promotion gate** *(media complessità)*  
Rimuovere la promozione automatica. Sostituirla con un comando esplicito che l'agente chiama quando vuole promuovere: `wiki.py promote --workspace <path> --page <path>`. Il comando verifica i criteri e scrive il risultato. L'autonomia dell'agente rimane, ma la promozione diventa un'azione deliberata, non un effetto collaterale del retrieval.

**C — Quality score composito** *(alta complessità)*  
Calcolare un quality score = `frequency × stability × source_quality`, dove `source_quality` riflette se la pagina è derivata da PDF/web primari (alto) o da sintesi (basso). Promuovere solo sopra una soglia del composito.

---

### T4 — Il layer identità non ha risoluzione dei conflitti

**Problema:** `self-reflect` scrive in `wiki/identity/` ma le correzioni comportamentali possono contraddirsi nel tempo. L'ultima scrittura vince silenziosamente.

**Soluzioni:**

**A — Conflict detection in self-reflect** *(media complessità, raccomandata)*  
Prima di scrivere una nuova regola di identità, `wiki_selfreflect.py` confronta semanticamente la nuova regola con le esistenti. Se trova similarità > 0.75 con direzione opposta, non sovrascrive — crea una entry `wiki/identity/conflicts/slug.md` con entrambe le versioni e data del conflitto. Il dashboard mostra i conflitti irrisolti. L'agente (o l'utente) li risolve esplicitamente.

```
wiki/identity/
  core.md           ← regole consolidate
  conflicts/
    summary-style-2026-05-29.md  ← "aggiungi riepilogo" vs "non aggiungere"
```

**B — Versioning delle regole** *(bassa complessità)*  
Ogni regola in `wiki/identity/` ha un campo `updated_at` e `supersedes`. Quando `self-reflect` aggiorna una regola, la vecchia non viene eliminata ma marcata `superseded: true`. Questo crea una history leggibile e permette rollback manuali.

---

### T5 — Staging e production nello stesso LanceDB

**Problema:** `staging_wiki_pages` e `wiki_pages` vivono nella stessa istanza. Un database corrotto o in lock colpisce entrambi simultaneamente.

**Soluzione raccomandata — Staging su file JSON manifest** *(media complessità)*  
Lo staging non ha bisogno di vector search — serve solo come lista di file da promuovere. Sostituire `staging_wiki_pages` con un file `.wiki-staging-manifest.json`:

```json
{
  "session_id": "abc123",
  "started_at": "2026-05-29T10:00:00Z",
  "pending": [
    {"tmp": "wiki-works/X/concepts/rag.md.tmp", "final": "wiki-works/X/concepts/rag.md"}
  ]
}
```

Il manifest viene scritto atomicamente (write + rename), LanceDB riceve solo i chunk finali dopo il commit. In caso di crash, il manifest è il recovery point — nessuno stato residuo nel database vettoriale.

---

### T6 — Deriva skill/documentazione

**Problema:** `wiki-core.md` e `AGENTS.md` devono restare sincronizzati. Il CI test verifica la presenza di stringhe, non la correttezza semantica.

**Soluzione raccomandata — Fonte unica di verità** *(bassa complessità)*  
Eliminare `AGENTS.md` come documento separato. Sostituirlo con un redirect a `skills/wiki-core.md`. Il contratto operativo con l'agente è wiki-core.md — tutta la documentazione deve puntare a quel file, non duplicarla. La deriva diventa impossibile perché esiste solo un documento.

Se AGENTS.md deve restare per compatibilità, aggiungere in testa:

```markdown
> ⚠️ This file is a human-readable summary. The authoritative agent protocol
> is `skills/wiki-core.md`. When they conflict, wiki-core.md wins.
```

---

## Rischio sistemico principale: deriva epistemica

I problemi T2 e T3 combinati creano un rischio che merita attenzione separata.

Un wiki con auto-sintesi attiva e promozione automatica può entrare in un ciclo di rinforzo degli errori:

```
Pagina errata ingested
    → recuperata spesso (alta popolarità)
    → promossa a wiki/ (layer distilled)
    → recuperata in più query (massima visibilità)
    → usata come fonte per nuove sintesi
    → errore amplificato
```

Non esiste un segnale interno che interrompa questo ciclo. Il sistema non ha un meccanismo di "dubbio" — non distingue tra conoscenza verificata e conoscenza plausibile.

**Mitigazione strutturale:** introdurre una `knowledge_tier` esplicita su ogni pagina:

| Tier | Fonte | Comportamento |
|------|-------|---------------|
| `verified` | PDF/web primario + revisione umana | Peso pieno nel retrieval |
| `inferred` | Auto-sintesi non rivista | Peso ridotto (0.7×), TTL 30gg |
| `provisional` | Synthesis-pending | Non usata nel retrieval standard |

Il retrieval vector search moltiplica il distance score per il peso del tier. Questo non elimina gli errori ma li isola e previene l'amplificazione.

---

## Priorità di intervento

| Priorità | Soluzione | Complessità | Impatto |
|----------|-----------|-------------|---------|
| 1 | T2-A: staging area per sintesi | Bassa | Previene deriva epistemica |
| 2 | T6: fonte unica (elimina AGENTS.md) | Bassa | Elimina deriva documentazione |
| 3 | T4-A: conflict detection in self-reflect | Media | Rende identità coerente |
| 4 | T1-A: post-op verification hint | Bassa | Riduce missed behavior-log |
| 5 | T5: staging manifest JSON | Media | Isola crash da DB corruzione |
| 6 | T3-B: promozione esplicita | Media | Rimuove amplificazione errori |
| 7 | Knowledge tier nel retrieval | Alta | Mitigazione sistemica completa |
