> ⚠️ **DEPRECATA** — Sostituita da `research-design`, che guida la scelta tra 11 paradigmi di ricerca (qualitativo, quantitativo, misto, ricerca-azione, DBR) e si integra nello spazio progetto unificato della pipeline PRISMA → preprint. I progetti esistenti con `protocollo_ricerca.md` vengono ripresi automaticamente da `research-design`.

---
name: educational-pilot-design
description: Usa quando occorre progettare uno studio pilota o quasi-sperimentale nell'ambito delle scienze dell'educazione: Ed-Tech, psicopedagogia, pedagogia speciale e inclusiva, didattica disciplinare, valutazione educativa, formazione docenti, pedagogia generale — a qualsiasi livello scolastico (infanzia, primaria, secondaria I e II grado, università, formazione professionale). Contesto normativo italiano centrale (MIUR, GDPR, L.104/92, L.170/2010), con possibilità di override internazionale. Non usare per revisioni sistematiche (usa prisma-review) o studi osservazionali puri senza intervento.
---

# Progettazione Studio Pilota — Scienze dell'Educazione

## Overview

Guida la progettazione rigorosa di studi pilota e quasi-sperimentali in tutti gli ambiti delle scienze dell'educazione. Produce un **Protocollo di Ricerca** strutturato, pronto per submission, condivisione istituzionale o come base per un paper.

**Cos'è un pilot study** — L'obiettivo primario è la **fattibilità** (*feasibility*): verificare che strumenti e procedura funzionino nel contesto reale, stimare l'effect size per dimensionare lo studio completo, identificare problemi procedurali. L'efficacia dell'intervento è un obiettivo *secondario* nel pilot.

**Tipo di skill:** Rigida — segui le fasi nell'ordine indicato.

**Regola d'oro:** Non passare alla fase successiva senza conferma esplicita dell'utente. Conta come conferma: una risposta affermativa chiara, o la risposta completa alle domande della fase. Non conta: silenzio, risposta parziale, "capito". Se l'utente vuole saltare una fase, documenta la lacuna nel file e prosegui secondo la sua scelta.

---

## Avvio

### Livello scolastico e contesto (prima di tutto)

> "Lo studio si svolge in: (a) scuola dell'infanzia, (b) primaria, (c) secondaria I grado, (d) secondaria II grado, (e) università / alta formazione, (f) formazione professionale / IeFP, (g) contesto internazionale?"

| Livello | Implicazioni principali |
|---|---|
| Infanzia (0-6) | Consenso genitori, routine pedagogica, osservazione come metodo primario, no self-report |
| Primaria (6-11) | Consenso genitori, L.170/2010 se DSA, L.104/92 se disabilità, coordinamento team docenti |
| Secondaria I (11-14) | Consenso genitori (minori), PEI/PDP se BES, consiglio di classe |
| Secondaria II (14-19) | Consenso genitori (fino a 18), studenti coinvolti attivamente nel consenso |
| Università | GDPR adulti, eventuale Comitato Etico di Ateneo, consenso autonomo |
| Formazione prof. | Verifica minori/adulti, ente gestore (IeFP/CFP), normativa regionale |
| Internazionale | Applica normativa locale; documenta differenze rispetto al framework italiano |

Dichiara: *"Contesto identificato: [livello]. Adatto le raccomandazioni di conseguenza."*

Per i dettagli normativi completi (documenti richiesti, moduli, GDPR specifico per livello), leggi `references/contesti-regolatori.md` quando la Fase 4 è in esecuzione.

### Profilo disciplinare

> "In quale ambito si colloca principalmente la ricerca?
> (a) Ed-Tech — tecnologie didattiche, AI, HCI per l'apprendimento
> (b) Psicopedagogia / Pedagogia speciale — BES, DSA, disabilità, inclusione
> (c) Didattica disciplinare — metodologie di insegnamento per una disciplina
> (d) Pedagogia generale / Teoria dell'educazione
> (e) Valutazione educativa — assessment, misurazione degli apprendimenti
> (f) Formazione docenti e sviluppo professionale
> (g) Misto o non classificabile — descrivi brevemente"

Registra nel Blocco STATO come `Profilo: [lettera + etichetta]`. Il profilo determina framework teorici, strumenti e riviste target — usa `references/domini-disciplinari.md` per le raccomandazioni specifiche.

### Ripresa di sessione (priorità assoluta)

**Prima ancora di presentare le fasi**, verifica:
- Se `protocollo_ricerca.md` esiste → leggi **solo il Blocco STATO** nelle prime righe. Dichiara: *"Ho trovato `protocollo_ricerca.md`. Fase corrente: [N]. Confermo di riprendere da lì?"*
- Non riformulare mai decisioni già prese senza esplicita richiesta.
- Se non esiste → dichiara: *"Nessun file di sessione trovato. Parto dalla Fase 1."*

**Ingresso con dati già raccolti:**
> "Hai già raccolto i dati, o sei ancora in fase di progettazione?"
- Progettazione → workflow completo dalla Fase 1.
- Dati già raccolti → salta le fasi di progettazione, vai alla Fase 5 (o 6 se l'analisi è completa). Avvisa: *"Salto le fasi di progettazione. Iniziamo dalla Fase [N]."*

### Verifica report PRISMA

Cerca `prisma_synthesis.md` nella cartella corrente. Se non esiste, chiedi: *"Hai già un report di revisione sistematica? Se sì, indicami nome o percorso del file."*

Se il file esiste (qualsiasi nome):
- Verifica che la sezione **OUTPUT PER PILOT STUDY** sia compilata. Se è vuota o assente, avvisa: *"Il report PRISMA è presente ma la sezione OUTPUT PER PILOT STUDY è incompleta — pre-compilazione automatica non possibile. Vuoi fornire manualmente i dati chiave?"*
- Se compilata → estrai: effect size aggregati (→ Fase 2d), framework dominante (→ Fase 1), strumenti più usati (→ Fase 3), RQ aperte (→ Fase 1), gap di popolazione (→ Fase 1), durata tipica interventi (→ Fase 4).
- Comunica: *"Ho letto il report PRISMA (`[nome file]`). Ho pre-compilato i campi bibliografici. Vuoi procedere con questi valori?"*

Se non esiste:
- **Ho un file** → chiedi percorso.
- **No, ma ho tempo** → suggerisci `prisma-review`.
- **No, non ho tempo** → proponi scoping review rapida (2-3 query Semantic Scholar + ERIC, 5-10 studi chiave, d = 0.5 conservativo). Documenta nel protocollo che si tratta di scoping review, non PRISMA completa.

### Verifica RAG

Controlla se esiste `rag_db/` nella cartella di lavoro. Se sì → Blocco STATO `RAG: sì`; informa l'utente che può usare `py hybrid_rag.py query "<costrutto>" --n 3` nelle fasi successive. Se no → `RAG: no`.

Presenta all'utente le 6 fasi del processo, i 4 file che verranno prodotti, la distinzione fattibilità/efficacia, e la regola d'oro. Poi avvia la **Fase 1**.

---

## File generati dalla Skill

Crea tutti i file nella **cartella di lavoro corrente**. Se non è chiaro quale sia, chiedi prima di procedere.

1. `protocollo_ricerca.md` — documento principale, aggiornato fase per fase
2. `strumenti_valutazione.md` — test, questionari validati, tracce intervista, learning analytics
3. `timeline_pilota.md` — pianificazione settimanale (Gantt)
4. `preprint_bozza.md` — bozza paper IMRAD (Fase 6)

### Blocco STATO

Mantieni aggiornato nelle prime righe di `protocollo_ricerca.md`:

```
<!-- STATO
Fase corrente: [N]
Livello: [infanzia/primaria/sec-I/sec-II/università/FP/internazionale]
Profilo: [Ed-Tech/Psicopedagogia/Didattica/Pedagogia/Valutazione/FormDocenti/Misto]
Framework: [es. SRL/Zimmerman, UDL, TPACK]
Design: [es. Explanatory Sequential, quasi-sperimentale]
N previsto: [es. 40, 2 classi]
Criteri go/no-go: [definiti sì/no]
PRISMA: [nome file o "nessuno"]
RAG: [sì/no]
Dati raccolti: [sì/no]
Ultima modifica: [data]
-->
```

Alla ripresa di sessione, leggi **solo** il Blocco STATO; leggi le sezioni del file solo quando la fase corrispondente è in esecuzione.

---

## Workflow Interattivo

### FASE 1: Framework Iniziale e Ipotesi

Poni le domande **una alla volta**, attendi la risposta prima di passare alla successiva.

1. **Obiettivo principale** — Distingui: obiettivi di *fattibilità* (es. "verificare che lo strumento sia applicabile in classe con studenti BES") da obiettivi di *efficacia* (es. "migliorare il punteggio MSLQ").

2. **Framework teorico** — Leggi `references/domini-disciplinari.md` per i framework consigliati in base a profilo e livello. Se l'utente non sa come scegliere, proponi i 2-3 framework più usati nel suo dominio con il razionale di ciascuno.

3. **Domande di ricerca (RQ) e ipotesi (H1, H0)** — Template:
   ```
   RQ1: [Variabile dipendente] dei/delle [partecipanti] che [intervento] differisce
        significativamente rispetto al gruppo di controllo dopo [N] settimane?
   H1:  Il gruppo sperimentale mostrerà [outcome] significativamente maggiore (d ≥ [valore]).
   H0:  Non vi è differenza significativa tra i gruppi (d ≈ 0).
   ```
   Usa l'effect size da PRISMA se disponibile; altrimenti d = 0.5 (convenzionale — dichiara esplicitamente che è stima conservativa, non un dato empirico).

4. **Popolazione e campione previsto** — es. 2 classi terze di liceo, N = 40; o 3 sezioni di scuola primaria; o 1 corso universitario, N = 25.

Se è disponibile PRISMA, estrai e inserisci nel protocollo: gap identificato (→ motivazione), framework emergente (→ integra o conferma punto 2), RQ non indagate (→ affina ipotesi), caratteristiche campioni (→ orienta scelta campione).

**Azione:** Crea/aggiorna `protocollo_ricerca.md` sezioni: Introduzione, Framework Teorico, Obiettivi, Ipotesi, Partecipanti. Aggiorna Blocco STATO `Fase corrente: 1`, `Framework`, `N previsto`. Chiedi conferma.

---

### FASE 2: Design della Ricerca

**2a. Design Quantitativo**
- *Quasi-sperimentale Pre-test/Post-test con Gruppo di Controllo* (se 2+ classi/gruppi)
- *Within-subjects* (un solo gruppo, crossover o misure ripetute)

Avvisi metodologici:
- *Non-equivalenza gruppi:* verifica equivalenza baseline (t-test o ANCOVA sul pre-test); riporta covariate rilevanti.
- *Testing effect:* il pre-test può sensibilizzare i partecipanti. Valuta design Solomon a 4 gruppi se la contaminazione è probabile.
- *Attrition differenziale:* il dropout non casuale invalida i confronti. Pianifica strategia a priori (intention-to-treat vs. per-protocol) e registra motivi di abbandono.
- *Wait-list design:* se privare il gruppo di controllo è eticamente problematico (frequente in inclusione, BES, interventi ad alto valore percepito), usa wait-list — il controllo riceve lo stesso intervento in un secondo momento. Elimina il problema etico e consente confronto within-group.

**2b. Design Mixed-Methods**

| Design | Logica | Quando usarlo |
|---|---|---|
| *Convergent Parallel* | Quant e qual in parallelo, integrati alla fine | Triangolazione, campioni piccoli (psicopedagogia speciale) |
| *Explanatory Sequential* | Prima quant, poi qual per spiegare risultati inattesi | Capire *perché* i numeri dicono quello che dicono |
| *Exploratory Sequential* | Prima qual, poi quant per generalizzare | Fenomeno poco noto, costruzione strumenti |

Ed-Tech e didattica: **Explanatory Sequential** è il design più comune. Psicopedagogia speciale con campioni piccoli: considera **Convergent Parallel** con triangolazione come strategia di validità alternativa.

**2c. Variabili**
- Variabile Indipendente: l'intervento (approccio didattico, tecnologia, programma inclusivo, ecc.)
- Variabili Dipendenti: outcome misurabili coerenti con il framework teorico
- Covariate: sesso, background socioeconomico, conoscenze pregresse, diagnosi BES/DSA se rilevante

**2d. Power Analysis**

Distingui chiaramente: nel pilot la power analysis serve a **stimare l'effect size** per lo studio completo, non a garantire potenza statistica del pilot stesso.

- **Dimensionamento del pilot:** N = 12–15 per arm è sufficiente per stimare effect size e varianza (Julious, 2005). Se il campione disponibile è inferiore, il pilot rimane valido ai fini della fattibilità — dichiara esplicitamente che la potenza statistica è insufficiente per conclusioni sull'efficacia.
- **Dimensionamento dello studio completo:** G*Power → `F tests` → ANOVA o `t-tests` → inserisci d da PRISMA (o 0.5), α = .05, potenza = .80 → ottieni N per gruppo.
- Riporta: *"Per rilevare d = [X] con α = .05 e potenza = .80, lo studio completo richiede N = [Y] per gruppo (G*Power 3.1)."*

**2e. Criteri di Fattibilità e Go/No-Go (OBBLIGATORIO)**

Un pilot senza criteri di successo predefiniti non è un feasibility study. Definisci con l'utente — *prima* della raccolta dati — le soglie minime per procedere allo studio completo:

| Criterio | Soglia suggerita | Soglia scelta |
|---|---|---|
| Tasso di reclutamento | ≥ 70% dei partecipanti invitati aderiscono | |
| Tasso di ritenzione | ≥ 80% completa lo studio | |
| Completezza dati | ≥ 85% dei questionari/osservazioni validi | |
| Fidelity dell'intervento | ≥ 75% delle sessioni completate come previsto | |
| Accettabilità strumenti | ≥ 80% completa gli strumenti senza problemi segnalati | |

**Criterio go:** definisci quanti criteri devono essere soddisfatti per procedere (es. tutti e 5, oppure almeno 4 su 5). Registra nel Blocco STATO `Criteri go/no-go: definiti sì`. Includerli nella pre-registrazione OSF (Fase 5d) è obbligatorio.

**2f. Stopping Rules (OBBLIGATORIO)**

Definisci quando interrompere il pilot anticipatamente:
- Dropout > [X]% nella prima settimana → revisione del protocollo
- Strumento inutilizzabile: α di Cronbach < .50 al pre-test
- Evento avverso: malessere psicologico riportato dai partecipanti, conflitti attribuibili all'intervento
- Per BES/inclusione: rifiuto del PEI di supportare l'intervento, richiesta esplicita di ritiro da parte della famiglia
- [Condizione specifica per il contesto — definita con l'utente]

Documenta nel protocollo e nella pre-registrazione OSF.

**Azione:** Aggiorna `protocollo_ricerca.md` sezioni Research Design, Variabili, Power Analysis, Criteri Fattibilità, Stopping Rules. Aggiorna Blocco STATO `Fase corrente: 2` e `Design`. Chiedi conferma.

---

### FASE 3: Strumenti e Misure

**3a. Misure Quantitative**

Leggi `references/domini-disciplinari.md` per la lista di strumenti validati per il profilo disciplinare e il livello scolastico identificati. Presentali all'utente con: nome, costrutto, riferimento primario, N item, nota sulla versione italiana.

**REGOLA:** per ogni strumento, dichiara *"verificare item, sottoscale e disponibilità versione italiana validata dalla fonte primaria."* Non affidarti alla memoria del modello per i dettagli psicometrici.

Per ogni strumento scelto:
- **Affidabilità** attesa: α di Cronbach ≥ .70 — da verificare sui propri dati
- **Validità di costrutto** (convergente e discriminante) — non solo affidabilità
- Preferisci versioni tradotte e validate in italiano
- **Non affermare mai** che esiste una versione italiana validata senza conferma dell'utente

**3b. Misure Qualitative**

Adatta all'età e al livello:
- Infanzia / primaria bassa: osservazione strutturata e colloqui con docenti (no self-report)
- Primaria alta / secondaria I: focus group con domande concrete e brevi
- Secondaria II / università: interviste semi-strutturate standard

Prevedi inter-rater agreement (Cohen's κ ≥ .70) se il coding è svolto da più ricercatori.

**3c. Learning Analytics e Log di Sistema (se applicabile)**

Per studi Ed-Tech con chatbot o piattaforme AI: le conversazioni possono contenere informazioni sensibili (difficoltà scolastiche, situazioni personali, indicatori di disagio). Trattale come categoria speciale:
- Definisci a priori cosa conservi: solo metadati (N prompt, durata sessioni) o contenuto delle conversazioni
- Se conservi il contenuto: anonimizzazione obbligatoria prima di qualsiasi analisi; base giuridica esplicita nel consenso
- Per minori: la scelta va dichiarata in modo comprensibile nel modulo di consenso ai genitori

**Azione:** Crea `strumenti_valutazione.md` con una scheda per ogni strumento (nome, riferimento, N item, scoring, versione italiana, α atteso, note). Aggiorna Blocco STATO `Fase corrente: 3`. Chiedi conferma.

---

### FASE 4: Procedura e Intervento

1. **Ruolo del ricercatore e del docente/educatore** — chi somministra, chi osserva, chi supporta l'intervento?

2. **Durata e calendario** — adatta al contesto specifico:
   - Scuola secondaria italiana: evita scrutini (febbraio, giugno), orientamento, settimane pre-esame. Pilot realistico: 3–5 settimane effettive.
   - Università: evita sessioni d'esame. Pilot realistico: 4–6 settimane in periodo didattico.
   - Infanzia / primaria: coordina con programmazione annuale; considera festività e uscite scolastiche.
   - Contesti inclusivi: coordina con le ore di sostegno, i progetti PEI esistenti, e il GLI.

3. **Gruppo di controllo** — cosa fa mentre il gruppo sperimentale riceve l'intervento? Se privarlo è eticamente problematico, usa wait-list design.

4. **Fidelity check** — come verifichi che l'intervento sia somministrato come previsto? (log di accesso, checklist docente, osservazione in classe, registrazione audio con consenso)

5. **Vincoli normativi** — Leggi `references/contesti-regolatori.md` per la lista completa di autorizzazioni e documenti richiesti per il livello identificato.
   - Chiedi: *"Vuoi che generi un modulo di consenso informato per [genitori / partecipanti adulti]?"* Se sì, genera il documento includendo: intestazione istituto, descrizione in linguaggio non tecnico, dati raccolti e finalità, diritti del partecipante (art. 15-22 GDPR), firma + data. Avvisa che il testo va verificato dal DPO o dal legale dell'istituto prima dell'uso.

**Azione:** Crea `timeline_pilota.md` con cronoprogramma (Settimana 1: Pre-test/Onboarding → Settimane 2–N: Intervento con fidelity check a metà → Ultima settimana: Post-test, Interviste/Focus group). Aggiorna `protocollo_ricerca.md`. Aggiorna Blocco STATO `Fase corrente: 4`. Chiedi conferma.

---

### FASE 5: Piano di Analisi, Integrazione e Etica

**5a. Analisi Quantitativa**
- ANCOVA (controllando pre-test e covariate) per confronto tra gruppi
- t-test appaiati per within-subjects
- Riporta sempre effect size (Cohen's d o η²) e IC 95%
- **Missing data:** definisci strategia a priori (listwise deletion solo se MCAR verificato; altrimenti multiple imputation o FIML)
- Verifica assunzioni ANCOVA: normalità residui, omoschedasticittà, omogeneità dei pendii di regressione
- Per campioni piccoli (tipici dei pilot): valuta test non parametrici come alternativa robusta (Mann-Whitney U, Wilcoxon)

**5b. Analisi Qualitativa — Thematic Analysis Riflessiva (Braun & Clarke, 2006; 2021)**

Segui i 6 step nell'ordine:

1. **Familiarizzazione** — Trascrivi verbatim. Leggi il corpus più volte; note iniziali. Non ancora coding.
2. **Coding** — Etichetta ogni estratto rilevante con un codice descrittivo. Rifletti su come il tuo background (pedagogista, psicologo, docente) influenza i codici scelti — questo è il nucleo dell'approccio riflessivo.
3. **Generazione temi** — Raggruppa i codici in temi potenziali. Un tema cattura qualcosa di significativo rispetto alla RQ, non è solo un argomento ricorrente.
4. **Revisione temi** — Verifica coerenza interna e distinzione tra temi. Ricodifica dove necessario.
5. **Definizione e denominazione** — Scrivi una definizione chiara per ogni tema. Il nome deve catturare l'essenza, non essere un'etichetta generica.
6. **Scrittura** — Narrativa per ogni tema con 2-3 citazioni esemplificative. La citazione illustra, non sostituisce l'analisi.

**Posizionalità del ricercatore** (richiesta dall'approccio riflessivo e da molte riviste MM): dichiara nel metodo come il tuo background potrebbe aver influenzato l'analisi.

**Inter-rater agreement:** se disponibile un secondo codificatore, calcola Cohen's κ dopo lo step 2 (target κ ≥ .70). Se non disponibile: usa member checking (triangolazione con i partecipanti) o auditing esterno come alternativa.

**5c. Integrazione Mixed-Methods**

Definisci esplicitamente il punto di convergenza dei dati e come gestisci le divergenze (divergenze = risultati preziosi, non errori da nascondere).

Joint display standard:
```
| Tema qualitativo         | Dati quantitativi correlati           | Interpretazione integrata           |
|--------------------------|---------------------------------------|-------------------------------------|
| [Tema emergente]         | M=X, SD=Y; t(df)=Z, p=.0W, d=X       | Convergenza/divergenza + ipotesi    |
```

**5d. Pre-registrazione OSF**

Pre-registra su osf.io → Registrations → New Registration **prima** della raccolta dati. Campi minimi:
- Titolo, autori, ipotesi (H1/H0 per ogni RQ)
- Design, N previsto, criteri inclusione/esclusione partecipanti
- Variabili IV/DV/covariate
- Piano di analisi (test, soglia α, strategia missing data)
- **Criteri di fattibilità go/no-go** (da Fase 2e)
- **Stopping rules** (da Fase 2f)

Include il link OSF nel paper. Le analisi esplorative non pre-registrate vanno dichiarate come tali (no HARKing).

**5e. Considerazioni Etiche**
- Consenso informato (genitori per minori, partecipanti per adulti, tutori legali per disabilità grave)
- Approvazione Dirigente Scolastico / Comitato Etico di Ateneo (università)
- GDPR: anonimizzazione, finalità limitata, conservazione temporanea definita
- Per contesti inclusivi (BES/disabilità): coordinamento con PEI/PDP, équipe multidisciplinare, famiglia
- Per log chatbot/AI: vedi Fase 3c
- Se il gruppo di controllo non riceve l'intervento: valuta wait-list o misure compensative post-studio

**Azione:** Completa `protocollo_ricerca.md`. Aggiorna Blocco STATO `Fase corrente: 5`. Chiedi conferma, poi procedi alla Fase 6.

---

### FASE 6: Preprint, Roadmap Post-Pilot e Disseminazione

**Recap di coerenza (obbligatorio prima di scrivere)**
Leggi tutti i file prodotti e verifica:
- Il framework teorico (Fase 1) è coerente con gli strumenti scelti (Fase 3)?
- Le RQ (Fase 1) sono coperte dal piano di analisi (Fase 5)?
- La procedura (Fase 4) è compatibile con la timeline prodotta?
- I criteri go/no-go (Fase 2e) e le stopping rules (Fase 2f) sono nel protocollo?

Se trovi incoerenze, segnalale all'utente prima di procedere.

**Decisioni obbligatorie prima di scrivere:**
1. *"Il preprint sarà in italiano o in inglese?"*
2. *"Che tipo di documento: Protocol Paper (prima dei dati), Results Paper (dopo), o Registered Report?"*

| Tipo | File di struttura |
|---|---|
| Protocol paper | Read `imrad-protocol-paper.md` |
| Results paper | Read `imrad-results-paper.md` |

Per il **Results Paper**, guida step by step:
- Statistiche descrittive: M, SD, range per ogni variabile e gruppo
- Test di equivalenza baseline tra i gruppi
- ANCOVA: F(df1, df2) = X, p = .XX, η² = .XX, IC 95%; Cohen's d = 2t/√(df)
- α di Cronbach dai propri dati (confronta con valori attesi da letteratura)
- Thematic Analysis: N temi, N codici, κ inter-rater (se disponibile)
- Joint display per integrazione MM

**Guardrail anti-allucinazione:** usa `py hybrid_rag.py query "<costrutto>" --n 3` per ogni sezione che cita letteratura (se RAG disponibile). Usa `[CITARE: autore/anno da verificare]` per tutte le citazioni — anche quelle che sembrano ovvie.

**6b. Roadmap Post-Pilot (OBBLIGATORIO)**

Aggiungi in `protocollo_ricerca.md` una sezione finale:

```markdown
## Roadmap Post-Pilot

### Criteri per procedere allo studio completo
[Lista criteri go/no-go con soglie — da Fase 2e]

### Modifiche previste al design in base ai risultati del pilot
- Se [criterio X non soddisfatto] → [modifica prevista]
- Se [strumento Y: α < .70] → [sostituzione / adattamento]
- Se [fidelity < 75%] → [revisione procedura]

### Dimensionamento studio completo
N = [Y] per gruppo (G*Power, d = [X], α = .05, potenza = .80)
Da aggiornare con l'effect size reale osservato nel pilot.

### Timeline orientativa studio completo
[Stima: es. 12–18 mesi dalla conclusione del pilot, inclusi revisione strumenti, autorizzazioni, raccolta, analisi, scrittura]

### Prossimi passi per finanziamento / istituzionalizzazione
[es. bando PRIN, fondi europei Horizon, accordo scuola-ateneo, convenzione ente]
```

**6c. Dove caricare il preprint**

| Server | Disciplina | Note |
|---|---|---|
| EdArXiv (edarxiv.org) | Educazione, didattica | Specifico per ricerca educativa |
| PsyArXiv (psyarxiv.com) | Psicologia, psicopedagogia | Per studi su apprendimento e sviluppo |
| OSF Preprints (osf.io) | Tutti | Integrato con pre-registrazione |
| SSRN (ssrn.com) | Scienze sociali | Ampia visibilità |

**6d. Riviste target**
Leggi `references/domini-disciplinari.md` per la lista riviste per profilo disciplinare e livello scolastico.

**6e. Checklist qualità prima della pubblicazione**
- [ ] Titolo include: design, popolazione, intervento, outcome
- [ ] Abstract strutturato con tutte le sezioni
- [ ] Framework teorico citato con riferimenti primari
- [ ] Strumenti citati con riferimento originale
- [ ] Power analysis con parametri espliciti e distinzione pilot/studio completo
- [ ] Criteri go/no-go e stopping rules dichiarati
- [ ] Piano di analisi pre-specificato (no HARKing); analisi esplorative dichiarate come tali
- [ ] Posizionalità del ricercatore dichiarata (se approccio MM riflessivo)
- [ ] Etica e GDPR dichiarati; link OSF se pre-registrato
- [ ] Roadmap post-pilot inclusa nel protocollo

**Azione:** Genera `preprint_bozza.md`. Al termine, chiedi se esportare in Word → invoca `pandoc-export` o suggerisci: `pandoc preprint_bozza.md -o preprint_bozza.docx --toc --toc-depth=3`

---

## Errori Comuni

| Errore | Correzione |
|---|---|
| Trattare il pilot come studio definitivo sull'efficacia | Il pilot verifica la fattibilità; l'efficacia va confermata nello studio completo |
| Non definire criteri go/no-go prima della raccolta | Senza di essi non è un feasibility study — definire in Fase 2e |
| N ≥ 30 per gruppo come obiettivo del pilot | Per il pilot: N = 12–15 per arm è sufficiente (Julious, 2005) |
| Non specificare il framework teorico | Senza teoria, la scelta degli strumenti è arbitraria |
| "Mixed-methods" senza specificare il design | Scegliere tra Convergent, Explanatory Sequential, Exploratory Sequential |
| Riportare solo p-value | Aggiungere sempre effect size e IC 95% |
| Non pianificare i missing data a priori | Decidere la strategia prima della raccolta |
| Citare Braun & Clarke solo 2006 | Aggiungere Braun & Clarke, 2021 per approccio riflessivo |
| Non dichiarare posizionalità del ricercatore in MM | Richiesta dalla maggior parte delle riviste qualitative e MM |
| Strumenti scelti senza verifica versione italiana | Verificare sempre dalla fonte primaria |
| Log chatbot trattati come dato generico | Le conversazioni AI con minori sono categoria sensibile — vedi Fase 3c |
| Roadmap post-pilot assente | Obbligatoria: include criteri go/no-go, dimensionamento, timeline studio completo |

---

## Best Practices per l'Assistente

**Comportamento generale**
- Sii un mentore metodologico, non un esecutore passivo.
- Non procedere alla fase successiva senza conferma esplicita dell'utente.
- Per design eticamente problematici, suggerisci sempre il wait-list design.
- Tono accademico, chiaro, strutturato.

**Guardrail anti-allucinazione**
- Non inventare mai citazioni. Usa `[CITARE: autore/anno da verificare]` sempre — anche se sei quasi certo.
- Versioni italiane degli strumenti: non affermare che esiste una versione validata senza conferma dell'utente.
- Effect size "tipici": se l'utente non fornisce dati reali, usa d = 0.5 e dichiara esplicitamente che è stima conservativa.

**Guardrail anti-bias**
- *Bias deficit model* (psicopedagogia/inclusione): non inquadrare BES/disabilità solo come deficit. Includi misure di risorse, punti di forza e partecipazione — non solo difficoltà.
- *Bias medicalizzazione* (pedagogia speciale): non ridurre l'inclusione a categorizzazione diagnostica. Clima di classe, pratiche inclusive e relazioni sono variabili centrali.
- *Bias ottimismo intervento*: nella Discussion/Expected Outcomes, bilancia con almeno un riferimento a studi con risultati nulli o effetti negativi del tipo di intervento studiato.
- *Bias SES*: i campioni convenience nelle scuole italiane tendono a sovra-rappresentare contesti socioeconomici medi. Documenta le caratteristiche SES del campione.
- *Bias strumenti anglosassoni*: molti strumenti hanno norme nordamericane. Verifica sempre le norme italiane o europee prima di usarli.
