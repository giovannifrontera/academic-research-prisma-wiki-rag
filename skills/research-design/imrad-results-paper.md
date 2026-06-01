# Struttura IMRAD — Results Paper *(dopo la raccolta dati)*

Genera `preprint_bozza.md` con questa struttura. Le sezioni 1 e 2 seguono la stessa struttura del
Protocol Paper (`imrad-protocol-paper.md`) — adattale ai risultati effettivi. La sezione 3 sostituisce
"Expected Outcomes" con i risultati reali.

**Guardrail anti-allucinazione:** Non inventare mai citazioni. Usa `[CITARE: autore/anno da verificare]`
per ogni riferimento bibliografico nella Discussion — anche se sei quasi certo. Se RAG disponibile:
usa `py hybrid_rag.py query "<costrutto>" --n 3` per ogni affermazione che cita letteratura.

---

```
## Abstract (strutturato, ~250 parole)
- **Background:** gap nella letteratura e framework teorico (uguale al protocol)
- **Objective:** obiettivi dello studio e domande di ricerca
- **Methods:** design, partecipanti, strumenti, procedura (sintesi)
- **Results:** risultati principali per ogni RQ (effect size se quantitativo, temi principali se qualitativo)
- **Conclusions:** implicazioni principali e contributo alla letteratura
- **Keywords:** 5-7 termini MeSH/ERIC

## 1. Introduction
  (uguale al Protocol Paper — contestualizza i risultati rispetto al gap originale)

## 2. Methods
  (uguale al Protocol Paper — descrivi ciò che è stato effettivamente fatto, non pianificato)
  Nota: se la procedura effettiva ha deviato dal protocollo, documenta e giustifica le deviazioni.

## 3. Results
### 3.1 Quantitative Results
  - Statistiche descrittive (M, SD, range) per ogni variabile e gruppo
  - Test di equivalenza baseline tra i gruppi
  - Risultati principali (ANCOVA/t-test) con effect size e IC 95%
  - Tabelle e figure in formato APA 7
### 3.2 Qualitative Results
  - Temi emersi dalla Thematic Analysis (con 2-3 citazioni esemplificative per tema)
  - Inter-rater agreement ottenuto (κ = ...)
### 3.3 Mixed-Methods Integration
  - Joint display o matrice di convergenza
  - Convergenze e divergenze tra dati quant e qual
  - Meta-inferenze: conclusioni che emergono solo dall'integrazione dei due fili

## 4. Discussion
  **Guardrail:** ogni affermazione che cita letteratura usa `[CITARE: autore/anno da verificare]`.
  - Interpretazione dei risultati rispetto alle RQ e al framework teorico
  - Confronto con letteratura esistente [CITARE]
  - Implicazioni per lo studio completo (effect size reale vs. stimato per power analysis)
  - Limiti dello studio
  - Direzioni future

## 5. Conclusions
  - Risposta sintetica alle domande di ricerca
  - Contributo teorico e pratico
  - Roadmap post-pilot (criteri go/no-go + dimensionamento studio completo)

## References
  (formato APA 7a edizione — solo fonti effettivamente citate nel testo)
```
