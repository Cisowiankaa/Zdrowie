# Release checklist — Zdrowie

## Przed publikacją
- [ ] `.env` nie jest commitowany.
- [ ] Brak tokenu Slack i klucza OpenAI w repozytorium.
- [ ] `python -m compileall -q .` przechodzi.
- [ ] Smoke import przechodzi.
- [ ] Lokalna baza SQLite nie znajduje się w repo.
- [ ] `documents/` i `backups/` są ignorowane.

## GitHub
- [ ] Repozytorium prywatne `Cisowiankaa/Zdrowie`.
- [ ] Branch główny `main`.
- [ ] GitHub Actions `Python CI` działa.
- [ ] Workflow `Build Windows` jest dostępny.

## Build Windows
- [ ] Uruchom workflow `Build Windows`.
- [ ] Pobierz artefakt `Zdrowie-Windows`.
- [ ] Uruchom aplikację bez `OPENAI_API_KEY`.
- [ ] Sprawdź tryb Online bez AI.
- [ ] Sprawdź tryb Offline.
- [ ] Jeśli jest klucz API, sprawdź Online + AI.
