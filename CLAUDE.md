# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SAPI-FXS4: kontext projektu

Port hudebního dema **Fuxoft Soundtrack IV** (František Fuka, ZX Spectrum, 27 skladeb pro AY-3-8912) na Tesla
SAPI-1, sestavu V (JPR-1V, RAM-1V, CGA-1V, MPH-1V), jako CP/M `.COM`. Repo `mlukasek/SAPI-FXS4`. Autor: Martin
Lukášek (mlukasek). Komunikace s autorem **česky**.

## Kde co je

- **Začni tady: `docs/SOUHRN.md`.** Obsahuje stav, postup na novém počítači (cesty, nástroje, jak spustit
  SAPIemu a zx84), kontrolu po změně, rozhodnutí autora, historii, další kroky a otázky k ověření na HW.
- **`docs/vyvoj.md`:** technika.
  - Soubory a příkazy, rozbor originálu (paměť, přehrávač, formát skladeb), jak vznikl disassembler.
  - Jak je port udělaný (paměť, obraz, scroller, časování, zvuk) a pasti.
- **`README.md`:** pro uživatele: co to je, spuštění, ovládání, skladby, rozdíly proti originálu.
- **Zdroje:**
  - `orig/fxs4.asm`: disassembler originálu, generuje ho `tools/mkdis.py` z `tools/annot.py`, needitovat;
  - `sapi/fxs4_sapi.asm`: port, ruční změny `SAPI:`;
  - `sapi/platform.asm`: hardware SAPI;
  - `sapi/tables.asm`: generuje `tools/make_tables.py`, needitovat.
- **Model přehrávače** `tools/player.py` je reference hudby (ověřený proti originálu v zx84).

## Zásady autora (dodržovat)

- **Napodobit funkci, ne Spectrum.** Obraz kreslit přímo na CGA-1V, „na první pohled podobný“. Žádné buffery
  ve formátu Spectra, převody ani věrné atributy.
- **Hudba se nesmí změnit:** registry AY portu musí tick po ticku sedět s `player.py`
  (`tools/emu/ay_check.py`).
- **Program musí končit pod `PROGRAM_LIMIT`** (B300h), hlídá to `tools/check_port.py` při překladu.
- **Měřit v emulátoru**, nehádat (`tools/emu/bench.py`, snímky přes `tools/emu/port.py`).
- **Testovat v `..\SAPIemu-release`** (`sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592`
  na pozadí). Port 8580 a vývojová verze `..\SAPIemu` patří autorovi. Když chce autor release vyměnit,
  `sapiemu-cli` ukončit.
- **Jazyk:** kód a komentáře v asm a skriptech **anglicky**, dokumentace **česky**.
- **Styl asm:** pasmo 0.5.3, komentáře s adresami Spectra zachovat, každou změnu označit `SAPI:` a napsat, co
  dělal originál. Pasti pasma jsou v globálním CLAUDE.md, pasti projektu v `docs/vyvoj.md` (Pasti).
- **Originál** `Demos/FXSOUND4.TAP` neměnit.
- **Git:** lokální commity průběžně, push jen na výslovné vyžádání. Na konec commitu řádek Co-Authored-By.
- **Dokumentace:** důležité poznatky zapisovat do `docs/` (na projektu se pracuje z více počítačů), stav
  a rozhodnutí do `docs/SOUHRN.md`.
- **Reálný HW:** autor ho má. Otázky k ověření sbírat v `docs/SOUHRN.md` (Nejasnosti k ověření na HW).
