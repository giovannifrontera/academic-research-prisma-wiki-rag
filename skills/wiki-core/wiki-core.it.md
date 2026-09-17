---
name: wiki-core
description: Protocollo wiki AI Agent v3 — cervello a tre layer, promozione autonoma, dedup semantico, auto-riflessione
---

# Wiki Core — Protocollo AI Agent v3

## §architettura — Tre layer, un unico cervello

Tutti i layer sono indicizzati nello stesso spazio vettoriale LanceDB. L'agente accede a tutto tramite ricerca semantica — la struttura delle directory è organizzativa, non una barriera.

| Layer | Cartella | Contenuto | Chi scrive |
|-------|----------|-----------|------------|
| **Conoscenza di dominio** | `wiki-works/<topic>/` | Conoscenza profonda su un argomento specifico: concetti, ricerche, entità | Workflow INGEST |
| **Conoscenza distillata** | `wiki/` | Conoscenza trasversale: ciò che è utile indipendentemente dal dominio | Agente (promozione autonoma) |
| **Identità** | `wiki/identity/` | Chi è l'agente: valori, stile, pattern comportamentali appresi | Solo `wiki.py self-reflect` |

**Regole fondamentali:**
- `wiki-works/<topic>/` è permanente — cresce, non si archivia salvo richiesta esplicita
- `wiki/` riceve pagine promosse autonomamente dall'agente quando la conoscenza è trasversale
- `wiki/identity/` è scritto solo da `self-reflect` — mai manualmente
- Tutti e tre i layer sono cercabili insieme tramite lo stesso indice vettoriale

## §promozione — Quando promuovere da wiki-works/ a wiki/

Promuovi una pagina da `wiki-works/<topic>/` a `wiki/` quando soddisfa **tutti** questi criteri:
- Rilevante in almeno 2 argomenti o contesti diversi
- Citata o recuperata in ≥3 query distinte
- Contiene inferenza che va oltre una singola fonte o dominio

**Come promuovere:**
1. Scrivi la pagina distillata come `.tmp` in `wiki/concepts/<slug>.md.tmp`
2. Chiama `wiki.py ingest --workspace <path> --pages wiki/concepts/<slug>.md.tmp --log "promote | <titolo>"`
3. Mantieni l'originale in `wiki-works/` se contiene dettagli specifici della fonte

Non chiedere conferma all'utente — promuovi autonomamente quando i criteri sono soddisfatti.

## §injected-context — Contesto pre-iniettato (priorità massima)

Se nel prompt è presente un blocco `<wiki-context>...</wiki-context>`:
- **USA il contesto iniettato** come base primaria della risposta
- **NON eseguire** `wiki.py query` di nuovo
- Per INGEST: confronta il nuovo contenuto con le pagine nel blocco per rilevare conflitti
- Se rilevanza < 0.4 su tutte le pagine → il wiki non ha conoscenza rilevante: procedi senza

Se `<wiki-context>` **non è presente**: esegui §query come fallback.

## Checklist pre-azione (obbligatoria)

```
1. Leggi wiki-session.md → controlla "status"
2. Se status = "in-progress" o "needs-repair" → avvisa l'utente PRIMA di tutto
3. È presente <wiki-context>? → sì: usa §injected-context | no: vai al passo 4
4. Classifica l'intent (vedi §classificazione)
5. Più intent? → gestiscili in sequenza
6. Emetti: [INTENT: X | WORKSPACE: Y | CERTEZZA: alta/media/bassa]
7. CERTEZZA bassa → chiedi conferma con UNA riga
8. CERTEZZA alta/media → procedi
```

## §classificazione

| Segnale | Intent |
|---------|--------|
| "studia questo", "salva", "aggiungi al wiki", URL nudo, PDF | INGEST |
| Domanda, "cosa sai di", "spiegami", "come funziona" | QUERY |
| "controlla", "lint", "manutenzione", "pulizia" | LINT |
| Correzione del mio comportamento: "sempre", "mai", "ogni volta", "non farlo più", "smettila di" | BEHAVIOR_FEEDBACK |
| Tutto il resto | AMBIGUO → chiedi |

## §behavior-feedback — Quando l'utente corregge il mio comportamento

Quando il messaggio è classificato come BEHAVIOR_FEEDBACK:

1. Normalizza la correzione in una frase breve e canonica
2. Chiama:
   ```bash
   py scripts/wiki.py behavior-log --workspace <path> --event "<frase canonica>"
   ```
3. Rispondi all'utente confermando la correzione
4. A fine sessione, esegui §self-reflect

## §self-reflect — Auto-riflessione autonoma

Da eseguire **sempre** a fine sessione se sono stati ricevuti BEHAVIOR_FEEDBACK, oppure se sono state ricevute ≥2 correzioni di qualsiasi tipo:

```bash
py scripts/wiki.py self-reflect --workspace <path>
```

Legge `.wiki-behavior-log.jsonl`, rileva pattern ricorrenti (≥3 occorrenze), aggiorna autonomamente `wiki/identity/`. Eseguila senza chiedere all'utente. Logga i cambiamenti in `wiki/log.md`.

## §ingest — Workflow INGEST (conoscenza in wiki-works/)

**Fase A — Ricerca:**
1. `web_search` per 5-10 fonti candidate
2. Applica quality filter: scarta fonti sotto score 6
3. `web_fetch` → salva in `wiki-works/<progetto>/raw/YYYY-MM-DD-slug.md`
4. Leggi le fonti, identifica punti chiave e conflitti

**Fase B — Scrittura:**
1. Scrivi pagine come `.tmp` in `wiki-works/<progetto>/`:
   - Entità → `entities/<slug>.md.tmp`
   - Concetti → `concepts/<slug>.md.tmp`
   - Sintesi → `synthesis/<slug>.md.tmp`
2. Chiama:
   ```bash
   py scripts/wiki.py ingest \
     --workspace <path> \
     --pages <p1.tmp,p2.tmp,...> \
     --log "ingest | <titolo>"
   ```
3. Se `status: error` → avvisa. Se `mini_lint: failed` → avvisa.

**Fase C — Report:** fonti usate, pagine create, conflitti risolti.
Dopo l'ingest, valuta i criteri §promozione per ogni nuova pagina.

## §lint — Workflow LINT

```bash
py scripts/wiki.py lint --workspace <path> --full
```

L'output JSON include `semantic_duplicates`. Gestiscili così:

| `action` | Cosa fare |
|----------|-----------|
| `auto_merge` (similarity ≥ 0.90) | Leggi entrambe le pagine, scrivi versione fusa come `.tmp`, chiama `wiki.py ingest`, cancella le originali |
| `warn` (0.75 ≤ similarity < 0.90) | Mostra all'utente con le prime 2 righe di ogni pagina e chiedi se unire |

Per i broken links e duplicati filename: presenta le opzioni all'utente.

## §query — Workflow QUERY

**Se `<wiki-context>` è presente:** salta i passi 1-3.

**Fallback manuale:**
1. `py scripts/wiki.py index --workspace <path>`
2. `py scripts/wiki.py query --workspace <path> --q "<domanda>" --k 5`
3. Leggi le pagine nei risultati

**Sempre:**
4. Sintetizza con riferimenti `[pagina](path)`
5. Se la risposta sintetizza ≥2 fonti wiki, supera 300 token, aggiunge inferenza non letterale → salvala come pagina via INGEST, poi valuta §promozione

## §pdf-inbox — Ingestione PDF

1. `py scripts/wiki.py ingest-pdf --workspace <path> --file <path|url>`
2. Per ogni path in `deposited`, leggi il file (testo grezzo estratto)
3. Struttura il testo grezzo in pagine `.tmp` in `wiki-works/<progetto>/`
4. Chiama `wiki.py ingest`

## §workspace — Selezione progetto

1. Leggi `wiki.config.json` → `projects` con keywords
2. Conta match tra parole chiave del messaggio e keywords
3. Progetto con più match → selezionato
4. Pareggio → chiedi all'utente

## §session

- Inizio sessione: leggi `wiki-session.md`
- Non modificare `wiki-session.md` direttamente: usa `wiki.py session-update`
- Se `status: in-progress`: avvisa prima di qualsiasi operazione
- Fine sessione con BEHAVIOR_FEEDBACK ricevuti: esegui §self-reflect
