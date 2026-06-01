# research-design Skill — Piano di Implementazione (Parte 2: Task 6–11)

> Continua da `docs/plans/2026-06-01-research-design-skill.md` (Task 1–5).

---

## Task 6: MOD-Q1 e MOD-Q2 — Fenomenologia e Grounded Theory

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Aggiungi MOD-Q1 e MOD-Q2**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## MOD-Q1 — Fenomenologia

*Attivato quando: D1=a, D2=a, D3=b*

**Riferimenti:** Smith, Flowers & Larkin (2009) — IPA; Giorgi (2009) — descrittiva; van Manen (1990)

**Cos'è:** studia l'esperienza vissuta (lived experience) di un fenomeno da una prospettiva in prima persona. L'obiettivo non è descrivere il fenomeno in sé, ma come esso è esperito dai partecipanti.

**Varianti principali:**
- *IPA (Interpretative Phenomenological Analysis)* — Smith et al.: idiografica, N=3-8, analisi tema per tema poi cross-case
- *Fenomenologia descrittiva* — Giorgi: epochò rigorosa, foci sul significato, no interpretazione

Chiedi: *"Preferisci IPA (più interpretativa, flessibile) o fenomenologia descrittiva (più rigorosa)?"*

### FASE 1 — Domande di ricerca e posizionamento

Formula le RQ come domande esplorative aperte:
- *"Come vivono l'esperienza di [X] i [partecipanti]?"
- "Quali significati attribuiscono a [fenomeno] i [partecipanti]?"
- "Come descrivono [partecipanti] la loro esperienza di [X]?"

**Posizionamento epistemologico:** dichiara il tuo punto di vista sul fenomeno (bracketing per IPA; epoché per Giorgi).

**Epoché / bracketing:**
Scrivi in `design/fase-1-framework/posizionamento.md` una riflessione su:
- Cosa pensi già del fenomeno
- Quali assunzioni porti con te
- Come metterai tra parentesi questi assunti durante l'analisi

**Azione:** Crea `design/fase-1-framework/framework-ipotesi.md` con domande di ricerca, framework fenomenologico scelto, posizionamento epistemologico.

### FASE 2 — Design fenomenologico

**N campione:** 3-8 partecipanti (IPA) o 6-12 (descrittiva). Più è piccolo, più l'analisi può essere profonda.

**Campionamento:** purposive (intenzionale) — chi ha esperienza diretta del fenomeno. Criteri di inclusione/esclusione legati all'esperienza del fenomeno, non alle caratteristiche demografiche.

**Sampling variation (IPA):** se vuoi confrontare perspettive diverse, includi partecipanti con background diversi (es. docenti esperti vs. novizi).

Crea `design/fase-2-design/design-ricerca.md` con: campione, criteri inclusione/esclusione, strategia di reclutamento.

### FASE 3 — Strumenti

**Intervista semi-strutturata:** il metodo primario.

Traccia intervista (da scrivere in `design/fase-3-strumenti/traccia-intervista.md`):
```markdown
## Traccia Intervista — [nome progetto]

**Apertura (5 min):**
"Puoi raccontarmi un momento specifico in cui hai vissuto/sperimentato [fenomeno]?"

**Domande esplorative (40-50 min):**
- "Come descriveresti questa esperienza?"
- "Cosa stava succedendo in quel momento?"
- "Cosa significava per te [X]?"
- "Cosa hai notato di diverso rispetto a prima?"
- "Come ti sei sentito/a durante [fenomeno]?"

**Chiusura (5 min):**
"C'è qualcosa di importante che non abbiamo discusso?"
```

**Durata:** 60-90 min. Registra con consenso. Trascrivi verbatim (incluse pause, "ehm", risate).

**Memo:** scrivi memo riflessivi dopo ogni intervista in `design/fase-3-strumenti/memo-[nome-partecipante].md`.

### FASE 4 — Procedura [→ §ETICA]

Reclutamento: annuncio in ambienti naturali del target (es. scuola, gruppo professionale). Seleziona chi ha esperienza diretta del fenomeno.

Procedura per ogni intervista:
1. Consenso informato (firma)
2. Spiegazione dello studio in linguaggio non tecnico
3. Intervista (registrazione audio con consenso)
4. Trascrizione verbatim entro 48h
5. Memo riflessivo post-intervista

Crea `design/fase-4-procedura/timeline.md`.

### FASE 5 — Piano di analisi (IPA)

**IPA — 6 passi (Smith et al., 2009):**

1. **Lettura e rilettura:** leggi ogni trascrizione più volte. Annota impressioni iniziali nel margine sinistro (commenti descrittivi e riflessivi).

2. **Note esplorative (Initial noting):** annota nel margine destro:
   - Commenti descrittivi (cosa dice il partecipante)
   - Commenti linguistici (come lo dice)
   - Commenti concettuali (cosa significa)

3. **Sviluppo temi emergenti:** raggruppa le note in temi. Ogni tema è una frase nominale che cattura l'essenza dell'esperienza (es. "Perdita di controllo sul tempo").

4. **Ricerca di connessioni tra temi:** mappa le relazioni tra temi. Identifica temi sovraordinati e subordinati.

5. **Passaggio al caso successivo:** ripeti i passi 1-4 per ogni partecipante senza guardare l'analisi degli altri.

6. **Pattern cross-case:** identifica temi condivisi, divergenti e idiosincratici. Decidi quali temi includere nel report (criterio: presenti in almeno N/2 + 1 partecipanti, oppure molto significativi anche se rari).

**Trustworthiness (Yardley, 2000):**
- *Credibility:* member checking (invia sintesi a 1-2 partecipanti per conferma), audit trail dettagliato
- *Transferability:* descrizione densa del contesto e del campione
- *Dependability:* journal riflessivo del processo di analisi
- *Confirmability:* citazioni esemplificative per ogni tema nel report

Crea `design/fase-5-analisi/codebook.md` e `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "fenomenologia",
  "variante": "IPA",
  "modulo": "MOD-Q1",
  "n_partecipanti": null,
  "metodo_analisi": "IPA-6-steps-Smith2009",
  "trustworthiness": ["member-checking", "audit-trail", "riflessivita"],
  "percorso_dati": "../raccolta-dati/dati/grezzi/trascrizioni/",
  "software_analisi": ["NVivo", "ATLAS.ti", "manuale"]
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura qualitativa (da `imrad-protocol-paper.md`). Nel metodo dichiara esplicitamente:
- Scelta del paradigma fenomenologico e rationale
- Posizionalità del ricercatore
- Strategie di trustworthiness adottate

---

## MOD-Q2 — Grounded Theory

*Attivato quando: D1=a, D2=b, D3=b (gap importanti, vuoi costruire teoria)*

**Riferimenti:** Glaser & Strauss (1967); Strauss & Corbin (1990) — GT classica; Charmaz (2014) — GT costruttivista

**Cos'è:** metodologia per costruire teoria ancorata ai dati empirici. Il prodotto finale è una teoria che spiega un processo sociale o psicologico, non una lista di temi.

**Varianti principali:**
- *Glaser & Strauss (classica):* emergenza pura dalla teoria, no sensibilizing concepts a priori
- *Strauss & Corbin:* paradigma di codifica (condizioni causali, fenomeno, contesto, strategie, conseguenze)
- *Charmaz (costruttivista):* co-costruzione con i partecipanti, sensibilizing concepts ok

Chiedi: *"Preferisci la GT classica (emergenza pura) o la GT costruttivista (Charmaz, più flessibile)?"*

### FASE 1 — Domande di ricerca

Formula come processo: *"Come/Cosa accade quando [situazione]?"* — non "Quali sono i fattori che..."

Esempi: "Come gestiscono i docenti l'integrazione dell'AI nelle pratiche valutative?" / "Cosa accade quando gli studenti DSA usano chatbot per lo studio?"

**Attenzione:** non formulare H1/H0. La GT non parte da ipotesi da verificare.

**Azione:** Crea `design/fase-1-framework/framework-ipotesi.md`.

### FASE 2 — Design GT

**Theoretical sampling:** il campione non è definito a priori — si decide chi intervistare in base ai temi emergenti dall'analisi in corso. Il campionamento si ferma alla saturazione teorica.

**Saturazione teorica:** nessuna nuova categoria emerge dalle nuove interviste. Non esiste un N fisso — tipicamente 20-30 interviste.

**Campionamento iniziale:** inizia con 5-6 partecipanti che hanno esperienza diretta del fenomeno. Poi il theoretical sampling guida chi intervistare.

Crea `design/fase-2-design/design-ricerca.md` con: campione iniziale, criteri theoretical sampling, criteri saturazione.

### FASE 3 — Strumenti

**Intervista semi-strutturata o non-strutturata:** traccia molto flessibile, si adatta a ogni partecipante.

**Memo writing (OBBLIGATORIO dall'inizio):**
Dopo ogni intervista e sessione di coding, scrivi un memo in `design/fase-3-strumenti/memo-[data].md`:
- Idee teoriche emergenti
- Connessioni tra codici
- Domande da esplorare nelle prossime interviste
- Ipotesi da verificare con il theoretical sampling

I memo sono parte integrante dell'analisi GT, non note a margine.

### FASE 4 — Procedura [→ §ETICA]

Il processo è iterativo: raccolta dati → analisi → theoretical sampling → raccolta dati → ... → saturazione.

Non separare raccolta e analisi: inizia a codificare dopo le prime 2-3 interviste.

Crea `design/fase-4-procedura/timeline.md` con fasi iterative e criteri di saturazione.

### FASE 5 — Piano di analisi

**Coding in 3 livelli:**

**Open coding:** leggi le trascrizioni riga per riga. Assegna un codice a ogni unità significativa. I codici sono descrittivi e vicini al testo (in vivo codes) o concettuali.

**Axial coding:** raggruppa i codici open in categorie più astratte. Per Strauss & Corbin: usa il paradigma di codifica (condizioni causali → fenomeno → contesto → strategie → conseguenze).

**Selective coding:** identifica la *core category* — il processo centrale che integra tutte le altre categorie. Tutta la teoria ruota attorno alla core category.

**Comparazione costante:** confronta costantemente incidenti, codici e categorie per affinarli.

**Diagramma delle categorie:** crea `design/fase-5-analisi/diagramma-categorie.md` con la mappa visuale delle relazioni tra categorie.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "grounded-theory",
  "variante": "Charmaz-costruttivista",
  "modulo": "MOD-Q2",
  "saturazione_criteri": "nessuna nuova categoria dopo N interviste consecutive",
  "coding_levels": ["open", "axial", "selective"],
  "percorso_dati": "../raccolta-dati/dati/grezzi/trascrizioni/",
  "software_analisi": ["NVivo", "ATLAS.ti", "manuale"]
}
```

### FASE 6 — Preprint [→ §PREPRINT]

L'output principale è la teoria substantiva. Nel paper:
- Presenta la core category e le categorie principali
- Mostra il processo teorico con un diagramma
- Valida la teoria con citazioni dirette dai dati (grounding)
- Dichiara il theoretical sampling e i criteri di saturazione
```

- [ ] **Step 2: Verifica**

```bash
grep -n 'MOD-Q1\|MOD-Q2' skills/research-design/SKILL.md | wc -l
# Atteso: almeno 8 righe
grep -n 'epoché\|bracketing' skills/research-design/SKILL.md
# Atteso: almeno 2 righe
grep -n 'core category\|selective coding' skills/research-design/SKILL.md
# Atteso: almeno 2 righe
```

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design MOD-Q1 fenomenologia IPA, MOD-Q2 grounded theory"
```

---

## Task 7: MOD-Q3, MOD-Q4, MOD-MM

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Aggiungi MOD-Q3, MOD-Q4, MOD-MM**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## MOD-Q3 — Etnografia

*Attivato quando: D1=a, D3=b, D-extra=a (pratiche collettive, cultura, contesto)*

**Riferimenti:** Geertz (1973); Hammersley & Atkinson (2007); Spradley (1980); Wolcott (1994)

**Cos'è:** studio intensivo e prolungato di un gruppo sociale nel suo contesto naturale. L'etnografo partecipa alla vita del gruppo per comprendere le pratiche culturali dall'interno.

### FASE 1 — RQ e posizionamento

RQ etnografiche: *"Come [gruppo] [fa/vive/gestisce/dà senso a X] nel loro contesto quotidiano?"*

**Ruolo dell'etnografo:** definisci il tuo ruolo lungo il continuum:
- *Partecipante completo:* l'osservatore partecipa pienamente (es. docente che studia la propria classe)
- *Partecipante-osservatore:* partecipa parzialmente
- *Osservatore-partecipante:* osserva con occasionali interazioni
- *Osservatore puro:* non interagisce con il gruppo

**Rifletti su:** accesso al campo, relazione con i gatekeepers, impatto della tua presenza sul gruppo.

**Azione:** Crea `design/fase-1-framework/framework-ipotesi.md` con RQ, ruolo scelto, riflessione posizionale.

### FASE 2 — Design etnografico

**Durata minima:** 3-6 mesi di presenza sul campo. Etnografie brevi (< 3 mesi) devono dichiarare esplicitamente i limiti.

**Negoziazione accesso:** identifica gatekeeper (dirigente, coordinatore). Prepara una lettera di presentazione dello studio. L'accesso va rinegoziato continuamente durante il campo.

**Selezione dei key informant:** 3-5 persone che conoscono bene il contesto e sono disposte a spiegarlo.

Crea `design/fase-2-design/design-ricerca.md`.

### FASE 3 — Strumenti

**Note di campo strutturate** (in `raccolta-dati/dati/grezzi/note-osservazione/AAAA-MM-GG.md`):
```markdown
## Note di campo — [data] — [luogo]

### Note descrittive
[Chi c'è, cosa fanno, come interagiscono, parole esatte usate]

### Note riflessive
[Le mie reazioni, ciò che mi sorprende, domande che mi vengono]

### Note teoriche
[Connessioni con la letteratura, ipotesi emergenti]

### Follow-up
[Chi devo intervistare, cosa devo osservare la prossima volta]
```

**Interviste con key informant:** semi-strutturate, registrate con consenso.

**Documenti istituzionali:** raccogli e analizza circolari, piani, materiali didattici, comunicazioni formali. Archivia in `raccolta-dati/dati/grezzi/documenti-istituzionali/`.

### FASE 4 — Procedura [→ §ETICA]

**Ethics ongoing:** il consenso in etnografia non è un documento firmato una volta — è un processo continuo di rinegoziazione. Chiedi periodicamente se le persone sono ancora a proprio agio con la tua presenza.

**Anonimizzazione:** decidi subito se usare pseudonimi per persone e luoghi. Documenta la scelta in `design/fase-4-procedura/anonimizzazione.md`.

Crea `design/fase-4-procedura/timeline.md` con fasi del campo: ingresso → esplorazione → approfondimento → uscita.

### FASE 5 — Piano di analisi

**Analisi tematica del campo:**
1. Leggi tutte le note di campo e trascrizioni
2. Identifica domini culturali (aree di significato condiviso)
3. Identifica tassonomie (come il gruppo classifica le cose)
4. Identifica temi culturali (principi ricorrenti che attraversano i domini)
5. Scrivi la *thick description* (Geertz) — descrizione densa che include non solo i fatti ma i loro significati culturali

**Triangolazione delle fonti:** incrocia note di campo, interviste e documenti per ogni tema.

Crea `design/fase-5-analisi/cronologia-eventi.md` e `design/fase-5-analisi/mappa-relazioni.md`.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "etnografia",
  "modulo": "MOD-Q3",
  "durata_campo_mesi": null,
  "metodo_analisi": ["thick-description", "domain-analysis", "taxonomic-analysis"],
  "triangolazione": ["note-campo", "interviste", "documenti"],
  "percorso_dati": "../raccolta-dati/dati/grezzi/"
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura qualitativa. La *thick description* è il cuore del report. Includi estratti dalle note di campo come evidence.

---

## MOD-Q4 — Ricerca Narrativa

*Attivato quando: D1=a, D3=b, D-extra=b (storie individuali, biografie)*

**Riferimenti:** Riessman (2008); Clandinin & Connelly (2000); Labov & Waletzky (1967)

**Cos'è:** studio delle storie che le persone raccontano della propria esperienza. L'assunto è che gli esseri umani danno senso alla loro vita attraverso narrative.

### FASE 1 — RQ

*"Quali narrative costruiscono [partecipanti] intorno a [esperienza]?"*
*"Come raccontano [partecipanti] il loro percorso di [X]?"*

Crea `design/fase-1-framework/framework-ipotesi.md`.

### FASE 2 — Design

**N campione:** 3-10 partecipanti. La profondità del caso prevale sul numero.

**Tipi di racconto:**
- *Life history:* storia di vita completa (retrospettiva, lunga durata)
- *Narrative episodico:* episodio specifico significativo
- *Story completion:* completamento di storie incomplete (proiettivo)

**Selezione:** partecipanti che hanno vissuto il fenomeno e sono in grado/disponibili a narrarlo.

Crea `design/fase-2-design/design-ricerca.md`.

### FASE 3 — Strumenti

**Intervista narrativa non direttiva** (Schuetze, 1983):
- Apertura molto ampia: *"Puoi raccontarmi la storia della tua esperienza di [X]? Prendi tutto il tempo che vuoi."*
- Lascia parlare senza interrompere (fase narrativa principale)
- Dopo: domande di approfondimento su episodi specifici emersi
- Finale: *"C'è qualcosa che non hai ancora detto e che ritieni importante?"

Documenti biografici integrativi: fotografie, diari, lettere (con consenso).

### FASE 4 — Procedura [→ §ETICA]

**Restituzione narrativa (member checking):** dopo l'analisi, condividi la tua interpretazione della storia con il partecipante. Discuti eventuali divergenze.

Crea `design/fase-4-procedura/timeline.md`.

### FASE 5 — Piano di analisi (Riessman, 2008)

**Approcci all'analisi narrativa:**

1. *Analisi tematica:* **cosa** viene raccontato — contenuto della storia
2. *Analisi strutturale* (Labov & Waletzky): **come** è strutturata la storia (abstract, orientation, complicating action, resolution, evaluation, coda)
3. *Analisi dialogica/performativa:* **perché** questa storia è raccontata ora, a chi, con quali effetti

In genere si usano 2-3 approcci in combinazione.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "ricerca-narrativa",
  "modulo": "MOD-Q4",
  "n_partecipanti": null,
  "approcci_analisi": ["tematica", "strutturale-Labov", "dialogica"],
  "percorso_dati": "../raccolta-dati/dati/grezzi/trascrizioni/"
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Presenta le storie con estratti narrativi estesi. Bilancia narrazione e analisi.

---

## MOD-MM — Mixed-Methods

*Attivato quando: D3=c (entrambi — triangolazione)*

**Riferimenti:** Creswell & Plano Clark (2018); Teddlie & Tashakkori (2009); Fetters et al. (2013)

**Varianti:**
- *Explanatory Sequential (QUAN → qual):* prima quantitativo, poi qualitativo per spiegare i risultati
- *Exploratory Sequential (qual → QUAN):* prima qualitativo, poi quantitativo per generalizzare
- *Convergent Parallel (QUAN + qual):* in parallelo, integrati alla fine per triangolazione

### FASE 1 — RQ

Formula **due set di RQ**: quantitative e qualitative, più la RQ mista che integra i due.

Es. Explanatory Sequential:
- RQ1 (quant): "L'intervento X migliora il punteggio MSLQ dei partecipanti?"
- RQ2 (qual): "Come spiegano i partecipanti i cambiamenti (o la mancanza) nel loro approccio allo studio?"
- RQ mista: "In che modo i risultati qualitativi aiutano a interpretare i risultati quantitativi?"

### FASE 2 — Design MM

**Punto di integrazione:** dove/quando i due fili si incontrano:
- Explanatory: dopo la fase quant, i risultati guidano il campionamento qual
- Exploratory: dopo la fase qual, i temi guidano la costruzione dello strumento quant
- Convergent: dopo entrambe le fasi, nel joint display

**Priority:** qual è il filo dominante (QUAN o qual)? Documenta la scelta e il rationale.

**Notazione MM:** usa la notazione standard:
- `QUAN → qual` = explanatory sequential, dominanza quant
- `qual → QUAN` = exploratory sequential, dominanza qual
- `QUAN + qual` = convergent, pari peso

Crea `design/fase-2-design/design-ricerca.md` con: variante MM, priority, punto di integrazione.

### FASE 3 — Strumenti

Definisci separatamente gli strumenti quant (vedi MOD-QN1/4 Fase 3) e qual (vedi MOD-Q1/3/4 Fase 3).

### FASE 4 — Procedura [→ §ETICA]

**Sequenza temporale:** disegna la timeline che mostra la sequenza delle due fasi e il punto di integrazione.

### FASE 5 — Piano di analisi

**Analisi quantitativa:** vedi piano analisi del modulo quant corrispondente.

**Analisi qualitativa:** vedi piano analisi del modulo qual corrispondente.

**Integrazione — Joint display:**

```
| Tema qualitativo         | Dati quantitativi correlati      | Interpretazione integrata        |
|--------------------------|----------------------------------|----------------------------------|
| [Tema emergente]         | M=X, SD=Y; d=Z, p=.0W           | Convergenza/divergenza + ipotesi |
```

**Gestione divergenze:** le divergenze tra fili quant e qual sono dati preziosi, non errori. Analizzale e riportale:
- *Convergenza:* entrambi i fili indicano la stessa direzione → corrobora la conclusione
- *Divergenza:* i fili indicano direzioni diverse → spiega perché, cosa significa, quali ulteriori analisi servono
- *Espansione:* il filo qual aggiunge dimensioni non catturate dal quant

**Meta-inferenze:** conclusioni che emergono dall'integrazione dei due fili e non sarebbero possibili con un solo metodo.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "mixed-methods",
  "variante": "explanatory-sequential",
  "modulo": "MOD-MM",
  "priority": "QUAN",
  "punto_integrazione": "dopo fase quantitativa",
  "filo_quant": { "modulo": "MOD-QN1", "test": ["ANCOVA"] },
  "filo_qual": { "modulo": "MOD-Q1", "metodo": "IPA" },
  "integrazione": "joint-display"
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura IMRAD con sezione Results divisa in: Quantitative Results + Qualitative Results + Mixed-Methods Integration.
```

- [ ] **Step 2: Verifica**

```bash
grep -n 'MOD-Q3\|MOD-Q4\|MOD-MM' skills/research-design/SKILL.md | wc -l
# Atteso: almeno 9 righe
grep -n 'joint display\|Joint display' skills/research-design/SKILL.md
# Atteso: almeno 2 righe
```

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design MOD-Q3 etnografia, MOD-Q4 narrativa, MOD-MM mixed-methods"
```

---

## Task 8: MOD-AR e MOD-DBR + tabella errori

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Aggiungi MOD-AR, MOD-DBR e tabella errori**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## MOD-AR — Ricerca-Azione (PAR)

*Attivato quando: D1=c (migliorare la pratica attraverso la ricerca)*

**Riferimenti:** Lewin (1946); Kemmis & McTaggart (1988); Reason & Bradbury (2008); Elliott (1991)

**Cos'è:** il ricercatore non studia la pratica dall'esterno — la trasforma dall'interno, insieme ai professionisti. L'obiettivo è simultaneamente produrre conoscenza e migliorare la pratica.

**Varianti principali:**
- *Action Research classica* (Lewin, Elliott): cicli riflessivi guidati dal ricercatore
- *PAR (Participatory Action Research)*: i partecipanti sono co-ricercatori, non oggetti
- *Critical PAR*: orientamento trasformativo, attenzione alle relazioni di potere

### FASE 1 — Problema e comunità

**Problema pratico:** non è una RQ accademica — è un problema reale vissuto dalla comunità.

> "Qual è il problema pratico che la comunità vuole risolvere?"
> "Chi sono i co-ricercatori? Qual è il loro ruolo nel progetto?"
> "Qual è l'obiettivo trasformativo della ricerca?"

**Comunità:** docenti, studenti, famiglie, operatori. Definisci chi partecipa e in quale ruolo.

**Obiettivo doppio:** produrre conoscenza (contributo accademico) + trasformare la pratica (contributo alla comunità).

Crea `design/fase-1-framework/framework-ipotesi.md`.

### FASE 2 — Design PAR: i cicli

Ogni ciclo segue la spirale di Kemmis:
1. **Pianificazione:** cosa facciamo? Perché? Come?
2. **Azione:** implementazione del piano
3. **Osservazione:** raccolta dati sull'azione (cosa succede?)
4. **Riflessione:** interpretazione collaborativa — cosa abbiamo imparato? Cosa cambiamo?

Il ciclo 2 parte dalla riflessione del ciclo 1. Pianifica 2-4 cicli.

Crea `design/fase-2-design/design-ricerca.md` con: N cicli previsti, durata ciclo, co-ricercatori.

Crea `raccolta-dati/dati/grezzi/cicli/ciclo-1/` con sottocartelle:
```
ciclo-1/
├── 01-pianificazione.md
├── 02-attuazione-log.md
├── 03-osservazioni.md
└── 04-riflessione.md
```

### FASE 3 — Strumenti

**Strumenti partecipativi:**
- *World cafè:* discussioni a piccoli gruppi rotanti su domande chiave
- *Focus group con co-ricercatori:* analisi collaborativa dei dati
- *Photovoice:* partecipanti fotografano aspetti della pratica e li commentano
- *Diario riflessivo del ricercatore:* journaling quotidiano

**Strumenti convenzionali:**
- Osservazione partecipante + note campo
- Interviste semi-strutturate
- Analisi documenti

### FASE 4 — Procedura [→ §ETICA]

**Consenso della comunità:** non solo consenso individuale — accordo collettivo (es. delibera del consiglio di classe, accordo dell'istituto). Documenta in `design/fase-4-procedura/consenso-comunita.md`.

**Etica della reciprocità:** la ricerca deve portare benefici alla comunità, non solo al ricercatore. Definisci come restituirai i risultati alla comunità.

Crea `design/fase-4-procedura/timeline.md` con: cicli, date incontri con co-ricercatori, scadenze.

### FASE 5 — Piano di analisi

**Analisi per ciclo:** dopo ogni ciclo, analizza i dati raccolti insieme ai co-ricercatori.

**Validazione collaborativa:** i co-ricercatori validano le interpretazioni. Le divergenze si risolvono per consenso o si documentano come tali.

**Spiral reflection:** dopo tutti i cicli, traccia l'evoluzione del problema e delle soluzioni attraverso i cicli. Crea `design/fase-5-analisi/sintesi-cicli.md`.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "action-research",
  "variante": "PAR",
  "modulo": "MOD-AR",
  "n_cicli": null,
  "co_ricercatori": [],
  "metodo_validazione": "validazione-collaborativa",
  "percorso_dati": "../raccolta-dati/dati/grezzi/cicli/"
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura PAR (da `imrad-protocol-paper.md`). Gli artefatti prodotti (strumenti rivisti, protocolli, materiali) sono output primari tanto quanto il paper.

---

## MOD-DBR — Design-Based Research

*Attivato quando: D1=d (progettare e raffinare iterativamente)*

**Riferimenti:** van den Akker et al. (2006); Reeves (2006); McKenney & Reeves (2012); Plomp & Nieveen (2013)

**Cos'è:** metodologia per progettare, implementare e raffinare interventi educativi (strumenti, curricula, ambienti) in cicli iterativi. Il prodotto finale è sia l'intervento migliorato sia la teoria che lo spiega (design principles).

### FASE 1 — Problema di design e teoria dell'intervento

> "Qual è il problema di design? (Es. gli studenti non riescono a usare il chatbot per l'apprendimento autonomo)"
> "Chi sono gli utenti target e qual è il contesto d'uso?"
> "Qual è la teoria dell'intervento iniziale? (Es. SRL + scaffolding progressivo)"

**Teoria dell'intervento:** ipotesi su come l'intervento produrrà i risultati attesi. Si raffina ad ogni iterazione.

**Design principles iniziali:** principi di design ipotetici che guidano la progettazione (es. "Il feedback immediato aumenta la metacognizione").

Crea `design/fase-1-framework/teoria-intervento.md` e `design/fase-1-framework/design-principles-iniziali.md`.

### FASE 2 — Design delle iterazioni

Ogni iterazione segue:
1. **Design:** (ri)progetta l'intervento/artefatto
2. **Implementazione:** usa l'artefatto nel contesto reale
3. **Analisi:** valuta cosa ha funzionato e cosa no
4. **Redesign:** modifica l'artefatto per l'iterazione successiva

Pianifica 2-4 iterazioni. La prima è spesso un prototipo grezzo.

Crea `raccolta-dati/dati/grezzi/iterazioni/iter-1/` con:
```
iter-1/
├── design-decisioni.md
├── implementazione-log.md
├── analisi-dati.md
└── redesign-decisioni.md
```

Crea `design/fase-2-design/changelog-artefatto.md` per tracciare le modifiche tra iterazioni.

### FASE 3 — Strumenti

**Usability data:** think-aloud protocols, heuristic evaluation, SUS (System Usability Scale)

**Learning data:** log di sistema (interazioni con l'artefatto), pre-post test, osservazione dell'uso

**Interviste post-sessione:** feedback strutturato degli utenti dopo ogni sessione

**Osservazione implementazione:** note di campo su come viene usato l'artefatto nel contesto reale

### FASE 4 — Procedura [→ §ETICA]

La timeline è iterativa, non lineare. Ogni iterazione ha la propria sotto-timeline.

Crea `design/fase-4-procedura/timeline.md` con tutte le iterazioni pianificate.

### FASE 5 — Piano di analisi

**Analisi comparativa tra iterazioni:** confronta sistematicamente i dati delle iterazioni per identificare miglioramenti e regressioni.

**Design principles emergenti:** alla fine di ogni iterazione, aggiorna i principi di design in `design/fase-5-analisi/principi-design.md` con evidenze dai dati.

**Raffinamento teoria dell'intervento:** aggiorna la teoria sulla base dei risultati osservati.

Scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "design-based-research",
  "modulo": "MOD-DBR",
  "n_iterazioni": null,
  "artefatto": null,
  "design_principles": [],
  "metodi_valutazione": ["usability", "learning-outcomes", "osservazione"],
  "percorso_dati": "../raccolta-dati/dati/grezzi/iterazioni/"
}
```

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura DBR (da `imrad-protocol-paper.md`). I design principles sono il contributo principale: presentali come output esplicito del paper.

---

## Errori comuni (tutti i paradigmi)

| Errore | Correzione |
|--------|------------|
| Cominciare senza verificare `.project-state.json` | L'Avvio è obbligatorio — mai saltarlo |
| Saltare Fase 0 e andare direttamente al design | La scelta del paradigma viene prima di qualsiasi altro passo |
| Non aggiornare `design/.research-state.json` a fine fase | Aggiornamento obbligatorio prima della conferma utente |
| Non appendere a `project-log.md` | Il log è la traccia permanente del progetto — ogni decisione va documentata |
| Pre-registrare OSF dopo l'inizio della raccolta dati | Pre-registrazione va fatta PRIMA della raccolta (Fase 2 per paradigmi quant) |
| Formulare H1/H0 per paradigmi qualitativi | Qualitativo = domande esplorative aperte, non ipotesi |
| Dichiarare N fisso a priori in GT | N dipende dalla saturazione teorica — non è predefinito |
| Fare solo 1-2 interviste in etnografia | Etnografia richiede minimo 3-6 mesi di campo |
| Non scrivere memo in GT | I memo sono parte integrante dell'analisi, non opzionali |
| Trattare la divergenza MM come errore | Divergenza = dato prezioso da analizzare e riportare |
| Consenso PAR solo individuale | PAR richiede anche consenso collettivo della comunità |
| Non citare i design principles nel paper DBR | I design principles sono il contributo principale del DBR |
| Inventare citazioni | Usa sempre `[CITARE: autore/anno da verificare]` |
| Non scrivere `piano-analisi.json` | Obbligatorio per handoff verso `data-analysis` |
```

- [ ] **Step 2: Verifica file completo**

```bash
grep -c '^## MOD-' skills/research-design/SKILL.md
# Atteso: 11 (MOD-QN1/2/3/4, MOD-Q1/2/3/4, MOD-MM, MOD-AR, MOD-DBR)
grep -c 'piano-analisi.json' skills/research-design/SKILL.md
# Atteso: almeno 10 (uno per modulo)
python3 -c "
import re
content = open('skills/research-design/SKILL.md').read()
modules = re.findall(r'^## MOD-', content, re.MULTILINE)
print(f'Moduli trovati: {len(modules)}')
assert len(modules) == 11, f'Atteso 11 moduli, trovati {len(modules)}'
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design MOD-AR ricerca-azione, MOD-DBR, tabella errori — SKILL.md completo"
```

---

## Task 9: Aggiorna `prisma-review` Fase 0

**Files:**
- Modify: `skills/prisma-review/SKILL.md`

- [ ] **Step 1: Leggi Fase 0 attuale di prisma-review**

Leggi `skills/prisma-review/SKILL.md` e individua la sezione **FASE 0 — Setup interattivo**.

- [ ] **Step 2: Aggiungi passo 0.0 (spazio progetto unificato)**

Nella sezione FASE 0, prima di qualsiasi altro passo (prima di "0.0 — Cartella di lavoro" attuale), inserisci:

```markdown
### 0.0 — Spazio progetto unificato

> "Come vuoi chiamare questo progetto di ricerca? (es. `review-chatbot-metacognizione`)"

Questa sarà la cartella root che ospita l'intero ciclo PRISMA → preprint. Crea la struttura completa:

```bash
mkdir -p <nome-progetto>/prisma
mkdir -p <nome-progetto>/rag_db
mkdir -p <nome-progetto>/design
mkdir -p <nome-progetto>/raccolta-dati/dati/{grezzi,elaborati,strumenti}
mkdir -p <nome-progetto>/analisi/{output,figure}
mkdir -p <nome-progetto>/preprint/output
```

Entra nella cartella root: tutti i comandi successivi vengono eseguiti da lì.

Inizializza **`.project-state.json`** nella root:
```json
{
  "progetto": "<nome-progetto>",
  "ricercatore": "[da chiedere]",
  "data_avvio": "<oggi>",
  "ultima_modifica": "<oggi>",
  "fase_workflow_corrente": "prisma",
  "fasi_workflow": {
    "prisma":            { "stato": "in-corso",   "data_avvio": "<oggi>" },
    "hybrid-rag":        { "stato": "non-avviata", "data_avvio": null },
    "research-design":   { "stato": "non-avviata", "data_avvio": null },
    "instruments-admin": { "stato": "non-avviata", "data_avvio": null },
    "data-analysis":     { "stato": "non-avviata", "data_avvio": null },
    "preprint":          { "stato": "non-avviata", "data_avvio": null }
  },
  "percorsi": {
    "prisma": "./prisma/",
    "rag_db": "./rag_db/",
    "design": "./design/",
    "raccolta_dati": "./raccolta-dati/",
    "analisi": "./analisi/",
    "preprint": "./preprint/"
  }
}
```

Inizializza **`project-log.md`** nella root:
```markdown
# Project Log — <nome-progetto>

**Ricercatore:** [nome]
**Data avvio:** <oggi>
**Pipeline:** PRISMA → RAG → research-design → instruments-admin → data-analysis → preprint

---
## [<oggi>] [prisma-review] Fase 0 — Avvio progetto
**Decisione:** Progetto creato. Struttura cartelle inizializzata.
```

> **Nota cartella di lavoro PRISMA:** tutti i file PRISMA (`prisma_state.json`, `raw_*.json`, ecc.) vanno creati in `<root>/prisma/`, non nella root del progetto.
```

- [ ] **Step 3: Aggiorna il passo "0.0 — Cartella di lavoro" esistente**

Subito dopo il nuovo 0.0, rinomina il vecchio "0.0 — Cartella di lavoro" in **0.0b — Cartella di lavoro PRISMA** e modifica la domanda:

```markdown
### 0.0b — Cartella di lavoro PRISMA

La cartella di lavoro PRISMA è già stata creata: `<root>/prisma/`. Tutti i file PRISMA verranno creati lì.

Salva il percorso in `prisma_state.json` come `cartella_lavoro: "./prisma/"`.
```

- [ ] **Step 4: Aggiorna Fase 0.8b (riepilogo) per includere il progetto**

Al termine della Fase 0 (step 0.8b), aggiungi:

```markdown
**Aggiorna `.project-state.json`:**
```json
{ "fasi_workflow": { "prisma": { "stato": "in-corso", "data_avvio": "<oggi>" } } }
```
**Aggiorna `project-log.md`:**
Appendi: `## [data] [prisma-review] Fase 0 completata \n**PICO:** [...] **Database:** [...] **Parametri:** [...]`
```

- [ ] **Step 5: Aggiorna fine Fase 6 per aggiornare `.project-state.json`**

In fondo alla sezione FASE 6 (Report finale), prima della sezione "Export in Word", aggiungi:

```markdown
**Aggiorna `.project-state.json`:**
```json
{
  "fase_workflow_corrente": "hybrid-rag",
  "fasi_workflow": {
    "prisma": { "stato": "completata", "data_completamento": "<oggi>" },
    "hybrid-rag": { "stato": "non-avviata" }
  }
}
```
**Aggiorna `project-log.md`:**
Appendi: `## [data] [prisma-review] Skill completata \n**N paper inclusi:** [...] **Prossimo passo:** hybrid-rag`
```

- [ ] **Step 6: Verifica**

```bash
grep -n 'project-state.json\|project-log.md' skills/prisma-review/SKILL.md | wc -l
# Atteso: almeno 4 righe
grep -n 'prisma/' skills/prisma-review/SKILL.md | head -5
# Atteso: riferimenti alla sottocartella prisma/
```

- [ ] **Step 7: Commit**

```bash
git add skills/prisma-review/SKILL.md
git commit -m "feat: prisma-review Fase 0 crea struttura progetto unificata + .project-state.json"
```

---

## Task 10: Aggiorna `pipeline-ricerca`

**Files:**
- Modify: `skills/pipeline-ricerca/SKILL.md`

- [ ] **Step 1: Riscrivi il flusso principale**

Leggi `skills/pipeline-ricerca/SKILL.md`. Sostituisci la sezione **Flusso completo** con:

```markdown
## Flusso completo

```
<root>/
├── .project-state.json          ← MASTER STATE (creato in PRISMA Fase 0)
├── project-log.md               ← log unificato append-only
├── prisma/                      ← [prisma-review]
│   ├── prisma_state.json
│   ├── eligibility_prisma.json
│   ├── prisma_synthesis.md        ← handoff → research-design
│   └── pdf_manuali/
├── rag_db/                      ← [hybrid-rag]
├── design/                      ← [research-design]
│   ├── .research-state.json
│   ├── fase-5-analisi/
│   │   └── piano-analisi.json     ← handoff → instruments-admin + data-analysis
│   └── fase-6-preprint/
│       └── preprint-bozza.md      ← handoff → pandoc-export
├── raccolta-dati/               ← [instruments-admin]
├── analisi/                     ← [data-analysis]
└── preprint/                    ← output finale
```

**Flusso skill:**
```
[prisma-review]           → eligibility_prisma.json + prisma_synthesis.md
       ↓
[hybrid-rag]              → rag_db/
       ↓
[research-design]         → design/ + piano-analisi.json
       ↓
[instruments-admin]       → raccolta-dati/ (da creare)
       ↓
[data-analysis]           → analisi/ (da creare)
       ↓
[pandoc-export]           → preprint/output/
```

**`.project-state.json`** è l'artefatto centrale: ogni skill lo legge all'avvio e lo aggiorna alla fine.
```

- [ ] **Step 2: Aggiorna la tabella Stage 3**

Sostituisci la sezione **Stage 3** (quella su `educational-pilot-design`) con:

```markdown
## Stage 3 — `research-design`

**Quando:** dopo `hybrid-rag`, per progettare lo studio empirico.

**Input richiesti:**
- `.project-state.json` (root) — stato pipeline
- `prisma/prisma_synthesis.md` (sezione OUTPUT PER PILOT STUDY) — pre-compila framework, effect size, strumenti, RQ
- `rag_db/` (opzionale) — abilita query RAG durante la progettazione

**File prodotti:**

| File | Contenuto | Consumato da |
|------|-----------|-------------|
| `design/.research-state.json` | Stato fase design | Ripresa sessione |
| `design/protocollo_ricerca.md` | Protocollo completo con Blocco STATO | `pandoc-export` (opz.) |
| `design/fase-5-analisi/piano-analisi.json` | Piano analisi pre-specificato | `instruments-admin`, `data-analysis` |
| `design/fase-6-preprint/preprint-bozza.md` | Bozza preprint (IMRAD adattato) | `pandoc-export` |
```

- [ ] **Step 3: Aggiorna entry point alternativi**

Aggiungi alla tabella **Entry point alternativi**:

```markdown
| `.project-state.json` esiste | Qualsiasi skill — leggi lo stato e riprendi dalla fase corrente |
| `design/.research-state.json` esiste | `research-design` — riprende dalla fase design interrotta |
| `design/piano-analisi.json` pronto | `data-analysis` direttamente |
| Solo export Word | `pandoc-export` direttamente |
```

- [ ] **Step 4: Aggiorna sezione "Handoff critico"**

Aggiungi o aggiorna la sezione handoff:

```markdown
## Handoff critici

**prisma-review → research-design:**
`prisma/prisma_synthesis.md` sezione OUTPUT PER PILOT STUDY (effect size, framework, strumenti, RQ aperte).

**research-design → instruments-admin / data-analysis:**
`design/fase-5-analisi/piano-analisi.json` (paradigma, variabili, test previsti, percorso dati).

**research-design → pandoc-export:**
`design/fase-6-preprint/preprint-bozza.md`

**Tutte le skill → tutte le skill:**
`.project-state.json` (master state) e `project-log.md` (diario).
```

- [ ] **Step 5: Verifica**

```bash
grep -n 'research-design\|project-state.json' skills/pipeline-ricerca/SKILL.md | wc -l
# Atteso: almeno 6 righe
grep -n 'educational-pilot-design' skills/pipeline-ricerca/SKILL.md
# Atteso: 0 righe (rimosso o solo nella nota di deprecazione)
```

- [ ] **Step 6: Commit finale**

```bash
git add skills/pipeline-ricerca/SKILL.md
git commit -m "feat: pipeline-ricerca aggiorna flusso per research-design + .project-state.json"
```

---

## Self-Review del piano

**Copertura spec (`docs/specs/2026-06-01-research-design-skill-design.md`):**

| Sezione spec | Task che la implementa |
|--------------|------------------------|
| §2 Struttura progetto unificata + `.project-state.json` | Task 9 (prisma-review Fase 0) + Task 2 (AVVIO) |
| §3 `.project-state.json` schema | Task 2 (AVVIO) |
| §4 Architettura skill + trigger | Task 2 (header) |
| §5 `.research-state.json` schema | Task 2 (Fase 0.0) |
| §6 Fase 0 decision tree D1-D5 | Task 2 (Fase 0) |
| §7 MOD-QN1 (quasi-sperimentale) | Task 4 |
| §7 MOD-QN2 (RCT) | Task 5 |
| §7 MOD-QN3 (Single-subject) | Task 5 |
| §7 MOD-QN4 (Survey) | Task 5 |
| §7 MOD-Q1 (Fenomenologia) | Task 6 |
| §7 MOD-Q2 (Grounded Theory) | Task 6 |
| §7 MOD-Q3 (Etnografia) | Task 7 |
| §7 MOD-Q4 (Ricerca Narrativa) | Task 7 |
| §7 MOD-MM (Mixed-Methods) | Task 7 |
| §7 MOD-AR (Ricerca-Azione) | Task 8 |
| §7 MOD-DBR (DBR) | Task 8 |
| §8 `piano-analisi.json` handoff | Task 5-8 (in ogni modulo Fase 5) |
| §9 Elementi trasversali (log, state, guardrail) | Task 2 (protocollo aggiornamento) + Task 8 (errori) |
| §10 Modifica prisma-review | Task 9 |
| §10 Modifica pipeline-ricerca | Task 10 |
| §10 Deprecazione educational-pilot-design | Task 1 |
| File di supporto (imrad-*.md, references/) | Task 1 |
| Sezioni comuni (§ETICA, §PREPRINT, §HANDOFF) | Task 3 |

**Tutti i requisiti dello spec coperti. Nessun placeholder. Nessuna sezione mancante.**
