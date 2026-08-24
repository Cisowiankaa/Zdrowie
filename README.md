# Zdrowie

Profesjonalna aplikacja desktopowa do zarządzania lekami, wizytami, badaniami, receptami, przypomnieniami, dokumentacją i synchronizacją Slack.

## Tryby pracy

- **ONLINE + AI** — internet, integracje i opcjonalne AI.
- **ONLINE bez AI** — internet i integracje działają, AI korzysta z lokalnego fallbacku.
- **OFFLINE** — aplikacja działa na SQLite i lokalnych plikach; synchronizacja uruchamia się po powrocie internetu.

## Moduły

- Dashboard
- Leki
- Wizyty
- Badania
- Recepty
- Przypomnienia
- Powiadomienia
- Dokumentacja
- Synchronizacja Slack
- Backup / Restore
- Asystent AI jako warstwa opcjonalna

## Uruchomienie

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python main_window.py
```

## Bezpieczeństwo

Nie commituj `.env`, tokenów Slack ani kluczy API. Dane lokalne (`*.sqlite3`, `documents/`, `backups/`) są wykluczone przez `.gitignore`.

## GitHub Actions

- `Python CI` sprawdza składnię i importy.
- `Build Windows` buduje artefakt aplikacji przez PyInstaller po ręcznym uruchomieniu lub tagu `v*`.
