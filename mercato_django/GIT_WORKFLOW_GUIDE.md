# Guida al Workflow Git per MercatoPro

Questa guida descrive come gestire i branch e come effettuare il merge delle modifiche sul branch principale (`main`).

## 1. Workflow dei Branch

Seguiamo il modello **Feature Branching**. Tutte le nuove funzionalità o correzioni di bug devono essere sviluppate su branch separati.

### Creazione di un nuovo branch
Prima di iniziare, assicurati di avere l'ultima versione di `main`:
```bash
git checkout main
git pull origin main
```

Crea un nuovo branch per la tua funzionalità:
```bash
git checkout -b feature/nome-della-tua-feature
# oppure per un bugfix
git checkout -b fix/descrizione-bug
```

## 2. Sviluppo e Commit

Mentre lavori, esegui commit frequenti con messaggi chiari:
```bash
git add .
git commit -m "feat: aggiunta gestione notifiche push"
```

## 3. Mantenere il Branch Aggiornato

È importante integrare periodicamente le modifiche che altri sviluppatori potrebbero aver apportato a `main`:
```bash
git checkout main
git pull origin main
git checkout feature/nome-della-tua-feature
git merge main
```
Risolvi eventuali conflitti, aggiungi i file risolti e completa il merge:
```bash
# Dopo aver risolto i conflitti nei file
git add .
git commit -m "chore: merge main in feature branch"
```

## 4. Effettuare il Merge su Main

Esistono due modi principali per fare il merge su `main`.

### Metodo A: Tramite Pull Request (Raccomandato)
Questo è il metodo standard per il lavoro di squadra e garantisce la revisione del codice.

1. Esegui il push del tuo branch su GitHub:
   ```bash
   git push origin feature/nome-della-tua-feature
   ```
2. Vai su GitHub e apri una **Pull Request** (PR).
3. Attendi che i test automatici (CI) passino e che un collega approvi la PR.
4. Una volta approvata, clicca il tasto **"Merge pull request"** su GitHub.

### Metodo B: Merge Locale (Solo per permessi diretti)
Se hai i permessi per scrivere direttamente su `main` e non è richiesta una PR:

1. Torna su `main`:
   ```bash
   git checkout main
   ```
2. Unisci il tuo branch:
   ```bash
   git merge feature/nome-della-tua-feature
   ```
3. Invia le modifiche al server:
   ```bash
   git push origin main
   ```
4. (Opzionale) Elimina il branch locale:
   ```bash
   git branch -d feature/nome-della-tua-feature
   ```

## 5. Risoluzione dei Conflitti

Se durante un merge ricevi un avviso di conflitto:
1. Apri i file indicati (cerca i marcatori `<<<<<<<`, `=======`, `>>>>>>>`).
2. Scegli quale codice mantenere.
3. Rimuovi i marcatori di conflitto.
4. Salva i file, esegui `git add` e poi `git commit`.

---
**Nota per l'ambiente cto.new:**
Se stai lavorando tramite l'agente AI di cto.new, il comando `finish` si occuperà automaticamente di gestire il commit e la preparazione della Pull Request per te.
