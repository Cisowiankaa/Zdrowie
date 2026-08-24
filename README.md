# Zdrowie

Profesjonalna aplikacja desktopowa do zarządzania lekami, lekarzami, wizytami, badaniami, receptami, przypomnieniami, dokumentacją i synchronizacją między komputerami.

## Tryby pracy

- **ONLINE + AI** — internet, integracje i opcjonalne AI.
- **ONLINE bez AI** — internet i integracje działają, AI korzysta z lokalnego fallbacku.
- **OFFLINE** — aplikacja działa na SQLite i lokalnych plikach; synchronizacja uruchamia się po powrocie internetu.

## Moduły v6

- Dashboard
- Leki
- Lekarze — specjalizacja, placówka, telefon, e-mail, notatki
- Wizyty — termin, lekarz, miejsce, notatki i status
- Badania
- Recepty — lek, kod recepty, ilość, ważność i status realizacji
- Inteligentne przypomnienia — 24 h i 2 h przed wizytą oraz 3 dni przed końcem ważności recepty
- Powiadomienia
- Dokumentacja
- Synchronizacja wielokomputerowa i Slack
- Backup / Restore
- Asystent AI jako warstwa opcjonalna

## Uruchomienie v6

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python main_v6.py
```

## Bezpieczeństwo

Nie commituj `.env`, tokenów, kluczy API ani danych medycznych. Dane lokalne (`*.sqlite3`, `documents/`, `backups/`) są wykluczone przez `.gitignore`. Synchronizacja wielokomputerowa korzysta z zaszyfrowanego pliku w folderze współdzielonym.

## GitHub Actions

- `Python CI` sprawdza składnię i importy.
- `Build Windows` buduje aplikację v6 przez PyInstaller po ręcznym uruchomieniu workflow lub tagu `v*`.
