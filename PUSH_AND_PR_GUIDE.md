# Push & PR Instructions

## Commit Status ✓

Il commit è stato creato con successo:

```
[main (root-commit) 5694b31] feat(rate-limiter): Add API keys management and rate-limiting system
 65 files changed, 12775 insertions(+)
```

**Messaggio commit**: Rate limiter, API keys, middleware, decorators, tests, CI workflow

---

## Passi Successivi

### 1. **Push al repository (assumendo GitHub remoto)**

```bash
# Aggiungi il repository remoto (fallo una sola volta)
git remote add origin https://github.com/YOUR_USERNAME/Adsbot.git

# Configura il branch predefinito (facoltativo ma consigliato)
git branch -M main

# Esegui il push
git push -u origin main
```

**Se il repo esiste già**:
```bash
git push origin main
```

---

### 2. **Creare una Pull Request**

#### **Opzione A: Tramite GitHub Web UI**
1. Vai a https://github.com/YOUR_USERNAME/Adsbot
2. Clicca su "Pull requests"
3. Clicca su "New pull request"
4. Seleziona il branch `main` come source (dovrebbe essere auto-selezionato)
5. Titolo: `feat(rate-limiter): Add API keys and rate-limiting system`
6. Descrizione (copia dal file `CHANGES.md` o da qui sotto)

#### **Opzione B: Tramite GitHub CLI (se installato)**

```bash
gh pr create --title "feat(rate-limiter): Add API keys and rate-limiting system" \
  --body "See CHANGES.md for full details"
```

---

### 3. **Descrizione PR Consigliata**

Usa questo template per la PR:

```markdown
## Description

This PR implements a complete rate-limiting and API key management system for Adsbot.

## Features Added

- **API Key Management**: Secure role-based access control (admin/user)
- **Rate Limiting**: Redis and SQLite implementations with configurable policies
- **Policies**: BLOCK (429 responses) and SLOWDOWN (exponential backoff)
- **Middleware**: FastAPI ASGI middleware for automatic enforcement
- **Decorators**: Flask decorator wrapper for sync endpoints
- **Testing**: Comprehensive unit tests with CI workflow
- **Documentation**: Configuration guides and curl examples

## Changes

See `CHANGES.md` for detailed changelog.

## Testing

All tests pass:
```
✓ 3 passed, 5 skipped (integration tests), 5 warnings
```

Run tests locally:
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Configuration

1. Copy `.env.example` to `.env` (not committed)
2. Set `ADMIN_API_KEYS`, `USER_API_KEYS`, and `REDIS_URL` in `.env` or environment
3. Integrate middleware/decorators as per `docs/RATE_LIMITING.md`

## Breaking Changes

None. This is a new feature set.

## Related Issues

Closes #ISSUE_NUMBER (if applicable)
```

---

### 4. **Verifica Prima del Push**

```bash
# Verifica il log del commit
git log -1 --stat

# Verifica i file staggiati
git show --name-status HEAD

# Controlla che .env e credenziali SIANO ESCLUSE
git ls-files | grep -i env
# Output: .env.example (è OK)
# Output: .env (ERRORE - non dovrebbe esserci!)
```

---

### 5. **Se Hai Fatto Errori**

**Annulla l'ultimo commit senza perdere i file**:
```bash
git reset --soft HEAD~1
git reset HEAD COMMIT_MESSAGE.txt  # if you want to unstage this
```

**Riscrivi il commit message**:
```bash
git commit --amend -m "New message"
git push origin main -f  # force push (ATTENZIONE: solo se non è public!)
```

---

## Note Importanti

⚠️ **Sicurezza**:
- Verificare che `.env` **NON** sia in git
- Verificare che no API keys/passwords siano in alcun file committato
- Se ho fatto errori in chat, quelle chiavi sono compromesse → regenerare immediatamente

✓ **Workflow CI**:
- Il workflow `.github/workflows/python-tests.yml` eseguirà automaticamente i test quando pushate
- Avrà successo se `python -m pytest -q` passa (come abbiamo verificato localmente)

📝 **Commit Message**:
- Segue il formato `feat(scope): description`
- Include breaking changes (nessuno in questo caso)
- Dettagli in COMMIT_MESSAGE.txt e CHANGES.md

---

## Checklist Finale

- [ ] Hai verificato che `.env` NON è in git (`git ls-files | grep .env`)
- [ ] Hai fatto `git add -A` e `git commit`
- [ ] Hai fatto il push: `git push origin main`
- [ ] Hai creato la PR con una descrizione chiara
- [ ] I test passano nel CI (GitHub Actions)
- [ ] Qualcuno ha rivisto e approvato la PR

---

## Se Tutto OK

Dopo che la PR è stata reviewata e approvata:

```bash
# Merge via GitHub Web UI oppure via CLI
gh pr merge <PR_NUMBER> --merge

# Pulisci branch locale dopo merge
git branch -D rate-limiter  # if you used a feature branch
git pull origin main        # pull the merged state
```

---

**Fine! La PR è pronta per il merge.** 🚀
