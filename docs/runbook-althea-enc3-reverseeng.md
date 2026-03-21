# Althea ENC3 Reverse Path

## Cel

Ten runbook oddziela prace R&D dla AltheaWorld od toru produktowego Mythibia/OTC-like.
Celem nie jest teraz integracja z produktem, tylko zdobycie twardych artefaktow potrzebnych
zeby zrozumiec format `ENC3`, punkt deszyfrowania i realne mozliwosci dalszej automatyzacji.

## Zweryfikowany baseline

- Rejestracja AAC jest automatyzowalna bez CAPTCHA.
- Launcher jest dystrybuowany jako instalator NSIS.
- Wlasciwy launcher dziala jako Electron (`ALauncher`).
- Manifest updatera jest publicznie dostepny z `http://altheaworld.org/updater/updater.php`.
- Runtime klienta wyglada jak OTC-like, ale assety/moduly sa opakowane w `ENC3`.
- Plain module injection nie powinien byc dalej traktowany jako zalozenie robocze.

## Separacja od produktu

Produktowy tor dostaw pozostaje na Mythibia/OTC-like.
Althea ENC3 jest osobnym strumieniem badawczym i nie blokuje build/deploy/test dla Starter v1.

## Material wejsciowy

- strona AAC: `https://altheaworld.org/register.php`
- download page: `https://altheaworld.org/downloads.php`
- launcher settings API: `https://altheaworld.org/api/launcher_settings.php`
- updater manifest: `http://altheaworld.org/updater/updater.php`
- artefakty lokalne: `artifacts/enc3/`

## Hipotezy robocze

1. `ENC3` jest warstwa pakowania/szyfrowania na assetach lub modulach loadera OTC-like.
2. Klucz lub procedura deszyfrowania musi byc dostepna po stronie klienta w runtime.
3. Najszybsza droga nie prowadzi przez zgadywanie formatu, tylko przez uchwycenie momentu
   odczytu/deszyfrowania w procesie.

## Fazy prac

### Faza 1. Inwentaryzacja binarek

Zadania:
- zidentyfikowac glowne binarki launchera i klienta
- zapisac hashe, rozmiary, zaleznosci DLL i zasoby
- odseparowac komponent updatera od komponentu runtime

Artefakty:
- `artifacts/enc3/althea/binary-inventory.md`
- `artifacts/enc3/althea/hash-manifest.txt`

### Faza 2. Statyczne rozpoznanie ENC3

Zadania:
- znalezc wystapienia stringu `ENC3`
- zmapowac funkcje otwierajace pliki assetow/modulow
- sprawdzic, czy format ma naglowek, magic bytes, dlugosc, checksumy

Narzędzia sugerowane:
- Ghidra
- Detect It Easy
- strings / FLOSS

Artefakty:
- `artifacts/enc3/althea/enc3-static-notes.md`
- `artifacts/enc3/althea/enc3-header-samples.bin`

### Faza 3. Dynamiczny punkt deszyfrowania

Zadania:
- uruchomic klient i sledzic `CreateFile`, `ReadFile`, `MapViewOfFile`
- uchwycic moment, w ktorym dane sa juz jawne w pamieci
- sprawdzic, czy modul Lua jest ladowany z dysku, archiwum czy bufora pamieci

Narzędzia sugerowane:
- x64dbg
- Process Monitor
- API Monitor

Artefakty:
- `artifacts/enc3/althea/runtime-trace.md`
- `artifacts/enc3/althea/procmon-events.csv`

### Faza 4. Decyzja architektoniczna

Na podstawie zebranych dowodow podjac jedna z decyzji:
- `A`: runtime patching/instrumentation jest realistyczne
- `B`: potrzebny jest loader-side hook
- `C`: koszt Althea jest za wysoki i pozostaje tylko tor OTC-like

Artefakt:
- `artifacts/enc3/althea/decision-record.md`

## Kryteria wyjscia

Ten runbook uznaje sie za wykonany, gdy mamy przynajmniej jedno z ponizszych:
- udokumentowany format naglowka `ENC3`
- potwierdzony punkt deszyfrowania w runtime
- twarda decyzje, ze Althea nie jest oplacalna produktowo na obecnym etapie

## Zasady wykonawcze

- Nie mieszac artefaktow Althea z Mythibia starter pack.
- Kazdy krok ma zostawiac plik dowodowy w `artifacts/enc3/althea/`.
- Nie przechodzic do implementacji bot/runtime injection bez dowodu z fazy 2 lub 3.
