---
name: pipeline-ricerca
description: Use when starting a new academic research project, switching between skills mid-workflow, or needing to know which files connect prisma-review, hybrid-rag, educational-pilot-design and pandoc-export. Reference for the complete PRISMA → RAG → Pilot → Preprint pipeline.
---

# Pipeline di Ricerca Accademica

**Percorsi e interprete:** risolvi `<PLUGIN_ROOT>` dalla posizione di questa skill installata (`skills/<nome>/SKILL.md`, due directory sopra). Sostituisci i segnaposto con path assoluti reali e usa `python` dal venv attivo su Windows/Linux. I dati restano nella cartella review; vedi [setup e modelli](../../docs/models-and-setup.md).


## Flusso completo

```
[wiki-query]             ← Fase 1.0: pre-search knowledge check su wiki_workspace
       ↓
[prisma-review]          → eligibility_prisma.json + prisma_synthesis.md
                            + raw_pdf_manual.json (Stream 2: PDF manuali, PRISMA 2020)
       ↓
[hybrid-rag]             → rag_db/  (index-prisma + index-pdf pdf_inclusi/)
       ↓
[wiki-ingest]            ← Export post-review: entity pages (paper inclusi) + synthesis page
       ↓
[educational-pilot-design]    → protocollo_ricerca.md + preprint_bozza.md
       ↓
[pandoc-export]          → preprint_bozza.docx
```

**wiki-query** e **wiki-ingest** richiedono `wiki_workspace` configurato (Fase 0.8 di `prisma-review`).
Vedi `skills/wiki-core/SKILL.md` per i comandi. I due step wiki sono opzionali ma abilitano la memoria cross-sessione.

Ogni skill è invocata tramite il tool **`Skill`** di Claude Code (es. `Skill("prisma-review")`).

---

## Stage 0 — Bootstrap dello studio isolato

**Quando:** sia il comando esplicito `/pipeline-ricerca nuova` sia un intento in linguaggio naturale ("iniziamo una nuova ricerca", "avviamo un nuovo studio") avviano lo stesso bootstrap, prima di qualunque altra fase.

```bash
python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "<nome studio>" --parent "<CURRENT_WORKSPACE>"
```

Il comando stampa un JSON con `status` e, sugli esiti positivi, `project_root` (la cartella sigillata dello studio, layout completo in [PROJECT-SPEC.md](../../docs/PROJECT-SPEC.md)). Prima di trattare quel `project_root` come studio attivo, **conferma sempre il path con l'utente** (mostralo esplicitamente, non assumere il default silenziosamente).

Gestione degli esiti:

| `status` | Significato | Reazione della skill |
|---|---|---|
| `created` | Nuovo studio inizializzato da zero | Conferma il `project_root` e procedi allo Stage 1 |
| `resumable` | Esiste già uno studio valido con lo stesso slug (`.project-state.json` coerente) | Chiedi all'utente se vuole riprendere quello studio prima di continuare — non riprendere in automatico |
| `error` con `kind: "directory_conflict"` | La cartella target esiste e contiene già file non riconducibili a uno studio valido | Mostra l'errore all'utente e fermati: non tentare retry automatici né sovrascritture |
| `error` con `kind: "unsafe_target"` | Il target è un symlink o altrimenti non sicuro da inizializzare | Mostra l'errore all'utente e fermati: non tentare retry automatici |

Da questo punto in poi tutti i dati dello studio (prisma, sources, database, wiki-memory, synthesis, design, preprint, export) vivono sotto `project_root`; il codice del plugin resta l'unico confine esterno in lettura.

---

## Stage 1 — `prisma-review`

**Quando:** all'inizio di un progetto, per costruire la base bibliografica.

**Input richiesti:** domanda di ricerca (PICO), parametri di configurazione (anni, database, lingua).

**File prodotti:**

| File | Contenuto | Consumato da |
|---|---|---|
| `prisma_state.json` | Stato operativo + lista paper inclusi + `wiki_workspace` | Ripresa di sessione |
| `prisma_log.md` | Log metodologico ufficiale per il paper | — |
| `raw_pdf_manual.json` | Metadati PDF trovati manualmente (Stream 2, PRISMA 2020) | `hybrid-rag` index-pdf, Fase 2 dedup |
| `screening_prisma.json` | Paper dopo deduplicazione cross-stream (con abstract) | Solo screening; non indicizzare come evidenza inclusa |
| `eligibility_prisma.json` / `extraction_table.json` | Paper inclusi con dati estratti completi | `hybrid-rag` (primario), wiki-ingest |
| `prisma_synthesis.md` | Sintesi tematica + **OUTPUT PER PILOT STUDY** + wiki export | `educational-pilot-design`, wiki-ingest |
| `prisma_bibliography.md` | Schede bibliografiche annotate | Report finale |

**File critico per il passaggio al Pilot:** `prisma_synthesis.md` — sezione **OUTPUT PER PILOT STUDY** (effect size aggregati, framework dominante, strumenti, RQ aperte, gap di popolazione, durata tipica interventi). Deve essere compilata durante la Fase 4, non solo alla fine.

---

## Stage 2 — `hybrid-rag`

**Quando:** dopo la Fase 4 di `prisma-review`, per costruire il database RAG per la generazione del report e per il pilot.

**Input richiesti:** `eligibility_prisma.json` (o `extraction_table.json`). Opzionale: `pdf_inclusi/` con soli PDF approvati in eligibility, tracciati nel log con DOI/ID, revisore, data e motivazione. Linee guida e materiali di contesto richiedono un indice separato.

**Comandi minimi:**
```bash
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" choose-backend --backend qdrant
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" init
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" index-prisma eligibility_prisma.json
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" status
```

> Per BGE usa `choose-model --model bge-m3` prima di `init`; senza scelta esplicita il modello resta MiniLM. Il backend default è Qdrant.

**File prodotti:**

| File/Cartella | Contenuto | Consumato da |
|---|---|---|
| `rag_db/` | Database vettoriale locale (LanceDB, ChromaDB o Qdrant) | `prisma-review` Fase 6, `educational-pilot-design` |
| `rag_db/config.json` | Modello attivo, backend, indicizzazione | Ripresa di sessione |

**Dipendenza:** esegui il template della skill installata direttamente; non occorre copiarlo. Mantieni la directory corrente sulla review per il corretto `rag_db/`. Non usare mai screening non filtrato come fallback.

---

## Stage 3 — `educational-pilot-design`

**Quando:** dopo `prisma-review` (e opzionalmente `hybrid-rag`), per progettare lo studio pilota. Copre tutti i livelli scolastici (infanzia, primaria, secondaria I e II, università, formazione professionale) e tutti i profili disciplinari delle scienze dell'educazione (Ed-Tech, psicopedagogia, pedagogia speciale, didattica, valutazione, formazione docenti).

**Input richiesti:**
- `prisma_synthesis.md` (sezione OUTPUT PER PILOT STUDY) — pre-compila automaticamente framework, effect size, strumenti, RQ
- `rag_db/` (opzionale) — abilita query RAG durante la progettazione

**File prodotti:**

| File | Contenuto | Consumato da |
|---|---|---|
| `protocollo_ricerca.md` | Protocollo completo (Blocco STATO + sezioni) | `pandoc-export` (opzionale) |
| `strumenti_valutazione.md` | Questionari, tracce intervista, LA | — |
| `timeline_pilota.md` | Cronoprogramma settimanale | — |
| `preprint_bozza.md` | Paper IMRAD (Protocol o Results) | `pandoc-export` |

---

## Stage 4 — `pandoc-export`

**Quando:** al termine di `prisma-review` (report finale) o `educational-pilot-design` (preprint).

**Input richiesti:** qualsiasi file `.md` da convertire.

**Output:** file `.docx` nella stessa cartella del sorgente.

---

## Entry point alternativi

| Situazione | Da dove partire |
|---|---|
| Primo progetto, nessun file | `prisma-review` Fase 0 |
| `prisma_state.json` esiste e valido | `prisma-review` — legge fase_corrente e riprende |
| `prisma_state.json` corrotto (JSON invalido) | Rinominalo in `prisma_state.json.bak`, avvisa l'utente, riparte da Fase 0 con i dati recuperabili da `prisma_log.md` |
| `eligibility_prisma.json` pronto, RAG non ancora costruito | `hybrid-rag` direttamente |
| `rag_db/` esiste, pilot non ancora avviato | `educational-pilot-design` — rileva automaticamente `rag_db/` |
| `protocollo_ricerca.md` esiste | `educational-pilot-design` — legge Blocco STATO e riprende |
| Dati già raccolti | `educational-pilot-design` Fase 5 (Results Paper) |
| Solo export Word | `pandoc-export` direttamente |

---

## Handoff critico: prisma-review → educational-pilot-design

La sezione **OUTPUT PER PILOT STUDY** di `prisma_synthesis.md` è l'unico meccanismo di trasferimento dati strutturato tra le due skill. Se questa sezione è vuota, `educational-pilot-design` dovrà raccogliere manualmente tutte le informazioni bibliografiche.

Campi da compilare in `prisma_synthesis.md` prima di avviare `educational-pilot-design`:

```markdown
### Effect size aggregati
| Outcome | N studi | Effect size medio | Range | Qualità evidenza |

### Framework teorici dominanti
[lista con frequenza]

### Strumenti di misura più usati
| Strumento | N studi | Outcome | Versione italiana |

### RQ non ancora investigate
[lista domande aperte]

### Gap di popolazione
[es. "Nessuno studio su secondaria italiana"]

### Durata tipica degli interventi
[Range min–max settimane; mediana]
```
