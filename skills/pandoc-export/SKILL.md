---
name: pandoc-export
description: Use when the user wants to convert a Markdown file to Word (DOCX), especially after completing a PRISMA systematic review or an educational pilot study design. Triggers on: "converti in Word", "esporta in docx", "pandoc", "salva come Word", output from prisma-review or educational-pilot-design skill.
---

# Pandoc Export: Markdown → DOCX

## Overview

Converte i file Markdown (output di `prisma-review` o `educational-pilot-design`) in Word (.docx) usando pandoc.

## Verifica installazione (PRIMO PASSO)

```bash
pandoc --version
```

Se il comando fallisce → pandoc non è installato. Su Windows 11:
```bash
winget install --id JohnMacFarlane.Pandoc
```
Alternativa (se winget non disponibile): scarica da pandoc.org/installing. Dopo l'installazione, riavvia il terminale.

**Fallback senza pandoc:** suggerisci di incollare il Markdown in un editor Word-compatible (es. Typora, Obsidian → Export, oppure VS Code con estensione Markdown PDF).

---

## File attesi dalle skill chiamanti

### Da `prisma-review`
| File | Contenuto | Quando esportare |
|---|---|---|
| `report_finale.md` | Report completo della review | Al termine della Fase 6 |
| `prisma_log.md` | Log metodologico dettagliato | Se richiesto dalla rivista |
| `prisma_bibliography.md` | Bibliografia annotata | Per allegare al paper |

### Da `educational-pilot-design`
| File | Contenuto | Quando esportare |
|---|---|---|
| `preprint_bozza.md` | Bozza del paper IMRAD | Sempre alla fine della Fase 6 |
| `protocollo_ricerca.md` | Protocollo completo | Per submission a scuola/ente |
| `strumenti_valutazione.md` | Questionari e tracce intervista | Per allegato metodologico |
| `timeline_pilota.md` | Cronoprogramma Gantt | Per condivisione con il team |

**Chiedi sempre:** *"Quali file vuoi esportare? Tutti e quattro o solo il preprint?"*

---

## Comandi

### Conversione singola (standard per paper accademici)
```bash
pandoc "file.md" -o "file.docx" --toc --toc-depth=3
```

### Con template Word personalizzato (raccomandato per submission)
```bash
pandoc "file.md" -o "file.docx" --reference-doc="template.docx" --toc --toc-depth=3
```

> **Nota:** `-V geometry:margin=2.5cm` è un'opzione LaTeX — non funziona per DOCX. I margini si impostano nel template `.docx` di riferimento.

### Conversione batch (tutti i file edtech in una volta)

**Bash / Git Bash:**
```bash
for f in preprint_bozza.md protocollo_ricerca.md strumenti_valutazione.md timeline_pilota.md; do
  pandoc "$f" -o "${f%.md}.docx" --toc --toc-depth=3
done
```

**PowerShell (Windows):**
```powershell
foreach ($f in @("preprint_bozza.md","protocollo_ricerca.md","strumenti_valutazione.md","timeline_pilota.md")) {
  pandoc $f -o ($f -replace '\.md$', '.docx') --toc --toc-depth=3
}
```

### Percorsi con spazi su Windows (usa sempre le virgolette)
```bash
pandoc "/path/to/your/project/report_finale.md" -o "/path/to/your/project/report_finale.docx" --toc --toc-depth=3
```

---

## Workflow interattivo

1. **Verifica pandoc** — esegui `pandoc --version`. Se fallisce, installa (vedi sopra).
2. **Identifica i file** — usa la tabella "File attesi" per sapere cosa convertire in base alla skill chiamante.
3. **Chiedi template** — *"Hai un template Word dell'università o della rivista? Se sì, indicami il percorso del file `.docx`."*
4. **Esegui la conversione** — singola o batch secondo la necessità.
5. **Verifica output** — conferma che il `.docx` esista nella stessa cartella del sorgente.

---

## Note sui contenuti specifici

**Tabelle Markdown** → convertite correttamente in tabelle Word. Se il layout è brutto, usa `--reference-doc` con uno stile tabella definito.

**Diagramma PRISMA in ASCII** → rimane testo monospaziato nel DOCX. Se la rivista richiede un diagramma grafico conforme alle linee guida PRISMA 2020, va ricreato manualmente in Word o con un tool dedicato (es. prisma-flow-diagram.vercel.app).

**Codice/blocchi monospace** → resi con font Courier nel DOCX. Nessuna azione necessaria per report PRISMA o protocolli pilot.

---

## Template di riferimento

Se l'utente non ha un template:
```bash
pandoc -o template_default.docx --print-default-data-file reference.docx
```
Apri `template_default.docx`, modifica gli stili (Heading 1, Normal, Table) e riusalo con `--reference-doc`.

---

## Errori comuni

| Errore | Fix |
|--------|-----|
| `pandoc: file.md: openBinaryFile: does not exist` | Path sbagliato — usa path assoluto con virgolette |
| `pandoc` non riconosciuto | Pandoc non installato o terminale non riavviato dopo installazione |
| Tabelle Word malformate | Usa `--reference-doc` con stile tabella definito |
| Template non trovato | Verifica il percorso del `.docx` passato a `--reference-doc` |
| Caratteri speciali mancanti | Aggiungi `--pdf-engine=xelatex` solo se esporti in PDF (non serve per DOCX) |
