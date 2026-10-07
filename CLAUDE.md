# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SAPI-FXS4: kontext projektu

Port **Fuxoft Soundtrack IV** (František Fuka, ZX Spectrum) na Tesla SAPI-1, sestavu V (JPR-1V, RAM-1V, CGA-1V,
MPH-1V), jako CP/M `.COM`. Repo `mlukasek/SAPI-FXS4`. Autor: Martin Lukášek (mlukasek). Komunikace s autorem
**česky**.

Program je hlavně přehrávač 26 skladeb A–Z pro **AY-3-8912** s rolujícím textem. Na Spectru potřebuje 128K
nebo 48K s interfacem Melodik.

## Stav

Zatím je tu jen originál `Demos/FXSOUND4.TAP` (1997). Port se bude dělat stejně jako `..\SAPI-Flappy`, které
slouží jako vzor:
- disassembler originálu se značkami `SAPI:`,
- HW vrstva v `platform.asm`,
- generované tabulky,
- `build.cmd`,
- ověřování proti originálu v emulátorech.

Strukturu, `README.md` a příkazy sem doplnit, až vzniknou.

## Originál (zjištěno rozborem TAP)

- **`FX SOUND 4`:** BASIC, autostart řádek 9000.
  - Vyžaduje 48K režim: při `PEEK 23388` ≠ 0 (BANKM, 128K režim) vypíše „PREPNETE PROSIM SPECTRUM DO 48K
    MODU“ a skončí.
  - Pak `CLEAR 26999`, nahraje kód a spustí ho.
- **`FXS4 CODE`:** **744Ah–FFFFh** (35766 B).
  - Hlavní smyčka BASIC: `RANDOMIZE USR 33890` (8462h).
  - Další vstupy: `USR 49500` (C15Ch) a `USR 50003` (C353h).
  - BASIC mění kód přes `POKE 34025` (C3h `jp` / CAh `jp z`) a `POKE 34049`.
  - Od 745Bh je rolující text, kolem 8180h–8430h jsou fonty.
- **Zvuk:**
  - Rutina na C585h zapisuje registry R13 až R0 ze stínové kopie C3E6–C3F3h (R0–R13) přes porty **FFFDh**
    (adresa) a **BFFDh** (data). Toto je hlavní místo pro náhradu AY na SAPI.
  - Na port 7FFDh (stránkování 128K) program nesahá. Proto by měl hrát i na 48K s interfacem kompatibilním
    s porty 128K (Melodik). Na HW to ověřeno není.
  - `out (FEh),a` je na C0FBh, C101h a D3FFh (border nebo beeper, neověřeno).
- **Přerušení:**
  - IM 2 s I = C2h, nastavené na C3A8h. Na FFFFh je 18h (`jr`), na FFF4h je `jp C3C4h` (obsluha).
  - Rytmus přehrávání je 50 Hz přerušení Spectra.
  - Návrat do IM 1 a I = 3Fh je na C16Fh.
- **Formát TAP:** bloky jsou délka 2 B LE + flag + data + XOR. Hlavička má 19 B (typ 0 program, 3 CODE).
- **Disassembler:** `..\Tools\z88dk\bin\z88dk-dis.exe -o 29770 -s <od> -e <do> fxs4.bin`, kde `fxs4.bin`
  jsou data bloku CODE bez flagu a XOR.

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
