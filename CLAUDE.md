# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SAPI-FXS4: kontext projektu

Port **Fuxoft Soundtrack IV** (František Fuka, ZX Spectrum) na Tesla SAPI-1, sestavu V (JPR-1V, RAM-1V, CGA-1V,
MPH-1V), jako CP/M `.COM`. Repo `mlukasek/SAPI-FXS4`. Autor: Martin Lukášek (mlukasek). Komunikace s autorem
**česky**.

Program je hlavně přehrávač 26 skladeb A–Z pro **AY-3-8912** s rolujícím textem. Na Spectru potřebuje 128K
nebo 48K s interfacem Melodik.

## Stav a kde co je

- **Začni tady:** `README.md`. Obsahuje paměť originálu, jak běží, přehrávač, jak vznikl disassembler,
  poznámky pro port a nejasnosti k ověření.
- **Originál:** `Demos/FXSOUND4.TAP` (1997). Blok CODE 744Ah–FFFFh, BASIC zavaděč vyžaduje 48K režim.
- **Disassembler:** `orig/fxs4.asm` je hotový a přeloží se bajt po bajtu stejně. Generuje ho
  `tools/mkdis.py` z anotací v `tools/annot.py`, **needitovat ručně**. Po změně anotací:
  `python tools\mkdis.py asm orig\fxs4.asm` a `python tools\check_orig.py` (musí hlásit OK).
- **Model přehrávače:** `tools/player.py` (formát skladeb v jeho hlavičce).
  - Dává rozložení dat skladeb pro disassembler a záznam registrů AY po tiknutích
    (`python tools\player.py log A 500`).
  - Je ověřený v zx84: všech 27 skladeb dává na 15 000 tiknutích stejné registry AY
    (`python tools\zx\ay_compare.py 15000`).
- **zx84 ze skriptů:** `tools/zx/` (klient MCP přes stdio, start originálu, srovnání AY, záznam
  provedeného kódu). Node.js je v `C:\Program Files\nodejs`, v `..\zx84` je `npm install` hotový.
- **Port:** `sapi/fxs4_sapi.asm` (kopie disassembleru se změnami `SAPI:`, edituje se ručně),
  `sapi/platform.asm` (CGA-1V, 82C54, klávesnice, PLOT/DRAW, AY → YM3812), `sapi/tables.asm` (generuje
  `tools/make_tables.py`, needitovat). Překlad `build.cmd`. Běží v SAPIemu při 4 MHz, při 2 MHz práce
  snímku nestačí. Podrobnosti v README (Port).
- **SAPIemu pro testy:** release `..\SAPIemu-release` (autor mezitím vyvíjí `..\SAPIemu`).
  - Spouštět `sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592` na pozadí ve složce
    release. Port 8580 patří GUI autora.
  - Skripty jsou v `tools/emu` (`port.py`, `ay_check.py`, `bench.py`).
- **Pravidla portu:**
  - **Program musí končit pod A000h** (buffer obrazovky Spectra), hlídá to `tools/check_port.py`.
    Volného místa je málo (teď asi 330 B).
  - Registry AY portu musí sedět s `player.py` (`tools/emu/ay_check.py`).

## Důležité poznatky o originálu

- **Zvuk:**
  - Jediné místo výstupu do AY je `ay_write` (C585h). V každém tiknutí (50 Hz, přerušení IM 2) zapíše
    R13 až R0 ze stínové kopie `ay_regs` (C3E6h) přes porty FFFDh a BFFDh.
  - Hardwarová obálka AY se nepoužívá.
  - Na port 7FFDh program nesahá, proto by měl hrát i na 48K s Melodikem (v emulátoru Spectaculator na 128K i 48K s Melodikem ověřeno, na HW ne; na port to vliv nemá).
- **Data skladeb:**
  - Jsou plně symbolická (`song_X`, `nt_`, `env_`, `fx_`), takže je jde přestěhovat.
  - Je jich 27: 26 na klávesách A–Z a jedna skrytá na A4A6h, kterou žádná klávesa nevybírá.
  - Příkaz 8Ch skladby Y volá kód, který zapisuje na 0000h. Na Spectru je tam ROM, na SAPI RAM.
  - Skladby E, F a R čtou jako efekt výšky ROM 0000–0026h, protože kanál bez příkazu 86h má efekt
    na 0000h. Port ty bajty potřebuje (`ROM_HEAD` v `player.py`).
- **Samomodifikace:** opravované operandy mají návěští `equ $-n` (seznam v README).
- **Animace čar:** strojový kód `lines` volá BASIC ve smyčce, kreslí přes ROM `DRAW`. Hudba, VU metry
  a scroller běží v přerušení.

## Hlavní problémy portu

- **Zvuk:** MPH-1V nemá AY, má **YM3812 (OPL2)** a časovač **82C54**, porty 50h–57h (viz
  `..\SAPIemu\docs\desky\MPH-1V.md`). Tóny, šum a obálky AY se musí převést na OPL2.
- **Paměť:**
  - Originál sahá až do FFFFh, včetně vektoru IM 2.
  - Na SAPI je C000–FFFFh za běhu CGA-1V (`OUT 63h`) a pod ní je CP/M (TPA do D5FFh, BDOS D606h).
  - Rozložení řeší README SAPI-Flappy (Paměť a porty).
- **Časování:**
  - Spectrum hraje na 50 Hz.
  - CGA-1V dává VBI 60 Hz, proto je pro 50 Hz nutné použít 82C54 na MPH-1V.
- **Obraz:**
  - Spectrum má 256×192 bodů, 1 bit na bod a atributy.
  - CGA-1V má 320×200 bodů a 2 bity na bod (`..\SAPIemu\docs\desky\CGA-1V.md`).

## Emulátory a nástroje (`E:\SAPI_GIT`)

- **zx84** (`..\zx84`, MCP `npm run mcp`, popis `mcp/README.md`):
  - AY má jen u modelů třídy 128K (`hasAY`). Interface Melodik k 48K neemuluje.
  - Originál pouštět na modelu `128k` v režimu 48 BASIC.
- **zx-spectrum-mcp** (`..\zx-spectrum-mcp`): jen 48K s beeperem a bez AY. Hodí se na obraz a časování, ne
  na hudbu.
- **SAPIemu** (`..\SAPIemu`):
  - sestava `machines/sapi1v.sapi`, MCP na `http://127.0.0.1:8580/mcp`;
  - MPH-1V emuluje YM3812 přes Nuked-OPL3;
  - chyby emulátoru se opravují tam.
- **pasmo 0.5.3** (`..\Tools\pasmo-0.5.3\pasmo.exe`): pasti jsou v globálním CLAUDE.md a v
  `..\SAPIemu\CLAUDE.md`.

## Pravidla (jako SAPI-Flappy)

- **Jazyk:** kód a komentáře v asm a skriptech **anglicky**, dokumentace **česky**.
- **Styl asm:** pasmo 0.5.3. Komentáře s adresami Spectra zachovat. Každou změnu označit `SAPI:` a popsat,
  co dělalo Spectrum.
- **Hudba se nesmí změnit:** obsah registrů AY musí být v každém přerušení stejný jako na Spectru.
  Ověřovat porovnáním se zx84 a teprve potom řešit převod na OPL2.
- **Měřit v emulátoru**, nehádat.
- **Originál:** `Demos/FXSOUND4.TAP` neměnit, pracovat s kopiemi.
- **Pasti:**
  - lokální návěští `.x` jsou v pasmo globální;
  - `read_memory` v SAPIemu vrací nejvýš 4096 B;
  - `cycles` v MCP SAPIemu počítá takty 4 MHz.
- **Git:** lokální commity průběžně, push jen na výslovné vyžádání. Na konec commitu řádek Co-Authored-By.
- **Reálný HW:** autor ho má. Otázky k ověření sbírat v README do „Nejasností k ověření na HW“. Patří sem
  i otázka, zda originál hraje na 48K s Melodikem.
- **Disk C: emulátoru** (`..\SAPIemu\work\ide\sapi_hdd.img`) je mimo repo. Po nahrání programu emulátor
  vypnout přes `power off`, ne zabít.
