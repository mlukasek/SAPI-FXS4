# SAPI-FXS4: souhrn a předávka

Stav projektu, postup na jiném počítači, rozhodnutí autora a další kroky. Technika je v `docs/vyvoj.md`,
popis pro uživatele v `README.md`.

## Stav (2026-10-07)

- **Port je hotový a běží v SAPIemu** (0.3.0-alpha, sestava `machines/sapi1v.sapi`) při 4 i 2 MHz:
  - obraz: rámeček s animací čar a cyklováním barev, nápis, texty, VU metry, duhový scroller;
  - hudba: všech 27 skladeb (A–Z a skrytá na `-`), ENTER zrychlení, SPACE nová animace, ESC do CP/M.
- **Hudba je ověřená:**
  - registry AY přehrávače portu sedí tick po ticku s modelem `tools/player.py`;
  - model sedí s originálem v zx84 u všech 27 skladeb na 15 000 tiknutích.
- **Zvuk YM3812:** převod z AY autorovi zní dobře.
- **Na skutečné sestavě V funguje** (ověřil autor 2026-10-07). Jediný rozdíl proti emulátoru: CGA-1V lehce
  „sněží“ (viz Nejasnosti).
- Repo `mlukasek/SAPI-FXS4`: commity jsou jen lokálně, push jen na výslovný pokyn autora.

## Postup na novém počítači

Složky jsou vedle sebe v `E:\SAPI_GIT` (jinde upravit cesty nebo proměnné prostředí).

| Co | Kde | K čemu |
|---|---|---|
| Python 3 | v PATH, jen standardní knihovna | všechny skripty v `tools/` |
| pasmo 0.5.3 | `..\Tools\pasmo-0.5.3\pasmo.exe` (jinde proměnná `PASMO`) | překlad portu a disassembleru |
| SAPIemu release | `..\SAPIemu-release` (teď 0.3.0-alpha) | spuštění a ověřování portu |
| zx84 | `..\zx84` + Node.js (`C:\Program Files\nodejs`), v `..\zx84` jednou `npm install` | originál: srovnání AY, záznam kódu, zachycení obrazovky |
| z88dk-dis | `..\Tools\z88dk\bin\z88dk-dis.exe` | jen pro ruční prohlížení kódu, skripty ho nepotřebují |

- **Na skutečný počítač** se `.com` přenáší přes sériovou linku XMODEMem (`DOCPM.COM` v CP/M sestavy V).
- **Překlad portu:** `build.cmd` → `build\fxs4.com`, `build\fxs4.hex`. Na to stačí Python a pasmo. Data
  obrazovky jsou v repu (`tools/zx_start_screen.bin`), zx84 netřeba.
- **SAPIemu pro skripty:** ve složce `..\SAPIemu-release` spustit na pozadí
  `sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592`.
  - Port 8580 patří GUI autora. Release je oddělený od vývojové verze `..\SAPIemu`, kterou autor mezitím
    překládá, a má vlastní disk C:.
  - Když autor chce release vyměnit, `sapiemu-cli` se musí ukončit.
  - Skripty v `tools/emu` si samy nabootují CP/M (volba 1) a uloží stav `cpm` do paměti emulátoru.
- **zx84:** skripty v `tools/zx` ho spouštějí samy přes stdio (`node node_modules/tsx/dist/cli.mjs
  mcp/server.ts`). ROM Spectra si zx84 při prvním spuštění stáhne do `mcp/.cache` (potřeba internet).
  - Varování npm o instalačních skriptech (esbuild) nevadí.
- **Claude Code:** `CLAUDE.md` v repu shrnuje pravidla. Globální pasti pasma jsou v uživatelském CLAUDE.md.

## Kontrola po změně

```
build.cmd                                  rem překlad, velikost, volné místo (teď asi 5,2 KB)
python tools\emu\port.py 4000 build\x.png  rem port v SAPIemu 4 s, snímek CGA-1V (prohlédnout)
python tools\emu\ay_check.py 300 AEFR-     rem hudba: registry AY portu proti modelu (výběr kláves)
python tools\emu\bench.py                  rem čas snímku při 4 a 2 MHz, zpožděné snímky
python tools\emu\block_check.py 100        rem barevné bloky ve scrolleru (chyba palety)
```

Po změně disassembleru (`tools/annot.py`): `python tools\mkdis.py asm orig\fxs4.asm` a `python
tools\check_orig.py` (musí hlásit OK). `sapi/fxs4_sapi.asm` se tím nemění, změny v něm jsou ruční.

## Rozhodnutí autora

- **Napodobit funkci, ne Spectrum.** Obraz se kreslí přímo na CGA-1V, „na první pohled podobný“. Žádné buffery
  ve formátu Spectra, věrné atributy ani jejich kolize. Hudba ale musí hrát přesně jako originál (registry
  AY tick po ticku).
- **Scroller:** plynulý posun 2 body za snímek (varianta 1b). Duha přebíhá přes text o písmeno za snímek
  (posun palety). Barvy písmen samy o sobě jako v originálu nejsou.
- **SPACE:** po novém startu animace se oblast animace vymaže. Na Spectru staré čáry zůstávaly.
- **Skrytá 27. skladba** (A4A6h, na Spectru bez klávesy) je na klávese `-`.
- **Hlavní cíl je 4 MHz** (sestava V má TURBO), 2 MHz má fungovat taky (teď stíhá, animace je pomalejší).
- Klávesnice se čte v přerušení 1300 Hz, protože Consul 262.3 na JPR-1V nemá 7474 (STROBE je pulz 1 ms).

## Historie (hlavní kroky)

| Commit | Co |
|---|---|
| 2641428 | originál `Demos/FXSOUND4.TAP`, CLAUDE.md |
| 82880d3 | symbolický disassembler `orig/fxs4.asm`, model přehrávače `tools/player.py` |
| ca7600e | ověření modelu a disassembleru v zx84 (ROM 0000–0026h jako efekt výšky) |
| 124be6e | první běžící port (ještě s bufferem obrazovky Spectra) |
| a2bc3de | oprava „čudlíků“ ve scrolleru (zápis palety se zakázaným přerušením) |
| 4f9d420 | port kreslí přímo na CGA-1V: 5,7 ms na snímek místo 13,3 |
| f872462 | duha scrolleru přes posun palety |
| 95b57d0 | animaci ukončuje jen SPACE jako na Spectru, ostatní klávesy jako 0 |
| 0543faf | SPACE vymaže animaci, skrytá skladba na `-` |

## Další kroky a nápady

- Sněžení CGA-1V na skutečné desce: vyzkoušet `fxs4.com` (paleta v zatemnění) a případně `fxs4diag.com`
  (viz Nejasnosti).
- Zvuk: jen když bude autor chtít jinou barvu tónu nebo šumu. Nápady jsou šum přes rytmický režim YM3812
  nebo jiná křivka hlasitosti AY. Všechno je v `opl_update` a `ym_regs` (`sapi/platform.asm`).
- 2 MHz: animace čar je pomalejší (10,4 čáry/s proti 18,4 na Spectru). Zrychlit by šla `plot_xor`
  (rychlejší výpočet adresy bodu, například tabulky zarovnané na stránky).

## Ověřeno na HW (2026-10-07, autor)

Port na skutečné sestavě V funguje: obraz CGA-1V v režimu EGA s paletou po pásech, přerušení z MPH-1V na
1300,7 Hz, klávesnice, zvuk YM3812.

## Nejasnosti k ověření na HW

- **CGA-1V lehce „sněží“ po celé obrazovce** (autor, verze 3498458). V SAPIemu se to neprojeví.
  - Možné příčiny: zápisy do palety Bt476 během kreslení (port je dělal každý snímek kdykoli), nebo přístupy
    CPU do videoram (scroller 480 bajtů za snímek, body čar, VU metry), kdyby čekání CPU na okno nestačilo.
  - **Zkouška na HW:**
    1. `build\fxs4.com`: paleta se už zapisuje jen v zatemnění (VBI ve STATUS D7). Když nesněží, byla
       příčinou paleta.
    2. Když sněží dál, `build\fxs4diag.com` (`build.cmd diag`): za běhu nic nekreslí, jen hraje a mění
       paletu v zatemnění. Když tahle verze nesněží, sněžení dělají přístupy CPU do videoram (otázka na
       CGA-1V a čekací stavy). Když sněží i tahle, jde o něco jiného (třeba samotné čtení STATUS
       nebo zápis CONFIG).
- Klávesnice Consul 262.3 bez 7474: čtení STROBE každých 0,77 ms se v praxi zatím neprojevilo ztracenými
  stisky (sledovat).
- Originál na 48K s interfacem Melodik: podle kódu hraje (jen porty FFFDh a BFFDh, 7FFDh ne). V emulátoru
  Spectaculator hraje na 128K i na 48K s Melodikem (ověřil autor), na skutečném HW to ověřené není. Na port
  to vliv nemá.
