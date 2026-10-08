# SAPI-FXS4: souhrn a předávka

Stav projektu, postup na jiném počítači, rozhodnutí autora a další kroky. Technika je v `docs/vyvoj.md`,
popis pro uživatele v `README.md`, změny po verzích v `docs/release-notes/`.

## Stav: verze 1.0.1 (2026-10-07)

- **Hotové a vydané:** GitHub release `v1.0.1` (`fxs4.com`, `fxs4.hex`), repo `mlukasek/SAPI-FXS4` (veřejné).
- **Ověřeno na skutečné sestavě V** (autor): obraz, hudba, klávesnice, bez „sněžení“ CGA-1V.
- **Ověřeno v SAPIemu** (0.3.0-alpha, sestava `machines/sapi1v.sapi`) při 4 i 2 MHz:
  - obraz: rámeček s animací čar a cyklováním barev, nápis, texty, VU metry, duhový scroller;
  - hudba: všech 27 skladeb (A–Z a skrytá na `-`), ENTER zrychlení, SPACE nová animace, ESC do CP/M.
- **Hudba je ověřená:**
  - registry AY přehrávače portu sedí tick po ticku s modelem `tools/player.py`;
  - model sedí s originálem v zx84 u všech 27 skladeb na 15 000 tiknutích.
- **Zvuk YM3812:** převod z AY autorovi zní dobře.
- **1.0.1:** opravený pád skladby D. Rychlé přerušení ukládalo registry na zásobník kanálu přehrávače,
  teď má vlastní zásobník (viz `docs/vyvoj.md`, Časování). Ověřeno v SAPIemu i autorem.
- **Git:** lokální commity průběžně, push a vydání jen na výslovný pokyn autora.

## Postup na novém počítači

Složky jsou vedle sebe v `E:\SAPI_GIT` (jinde upravit cesty nebo proměnné prostředí).

| Co | Kde | K čemu |
|---|---|---|
| Python 3 | v PATH, jen standardní knihovna | všechny skripty v `tools/` |
| pasmo 0.5.3 | `..\Tools\pasmo-0.5.3\pasmo.exe` (jinde proměnná `PASMO`) | překlad portu a disassembleru |
| SAPIemu release | `..\SAPIemu-release` (teď 0.3.0-alpha) | spuštění a ověřování portu |
| zx84 | `..\zx84` + Node.js (`C:\Program Files\nodejs`), v `..\zx84` jednou `npm install` | originál: srovnání AY, záznam kódu, zachycení obrazovky |
| z88dk-dis | `..\Tools\z88dk\bin\z88dk-dis.exe` | jen pro ruční prohlížení kódu, skripty ho nepotřebují |
| GitHub CLI | `gh` (přihlášený účet mlukasek) | vydání (release) |

- **Na disk C: vývojového SAPIemu** (`..\SAPIemu\work\ide\sapi_hdd.img`, mimo repo; u autora je tam
  `C:FXS4.COM`):
  - spustit `..\SAPIemu\out\build\windows-release\sapiemu-cli.exe --data-root E:\SAPI_GIT\SAPIemu --machine
    machines/sapi1v.sapi --mcp --mcp-port 8593` (ne 8580, to je GUI autora);
  - přes MCP: `resume`, boot volbou `3` (CP/M s IDE diskem), `load_binary` `build\fxs4.com` na 0100h,
    `type_text` „`SAVE 159 C:FXS4.COM\r`“ (stránky vypíše `build.cmd`), kontrola `STAT C:FXS4.COM`;
  - nakonec `power off` (ne zabít) a `sapiemu-cli` ukončit.
- **Na skutečný počítač** se přenáší přímo `.com`, kterýmkoli způsobem, který sestava V umí (autor používá
  např. XMODEM přes sériovou linku programem `DOCPM.COM`).
- **Překlad portu:** `build.cmd` → `build\fxs4.com`, `build\fxs4.hex`. Na to stačí Python a pasmo. Data
  obrazovky jsou v repu (`tools/zx_start_screen.bin`), zx84 netřeba.
- **SAPIemu pro skripty:** ve složce `..\SAPIemu-release` spustit na pozadí
  `sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592`.
  - Port 8580 patří GUI autora. Release je oddělený od vývojové verze `..\SAPIemu`, kterou autor mezitím
    překládá, a má vlastní disk C:.
  - Když autor chce release vyměnit, nebo už ho nepotřebujeme, `sapiemu-cli` ukončit.
  - Skripty v `tools/emu` si samy nabootují CP/M (volba 1) a uloží stav `cpm` do paměti emulátoru.
- **zx84:** skripty v `tools/zx` ho spouštějí samy přes stdio (`node node_modules/tsx/dist/cli.mjs
  mcp/server.ts`). ROM Spectra si zx84 při prvním spuštění stáhne do `mcp/.cache` (potřeba internet).
  - Varování npm o instalačních skriptech (esbuild) nevadí.
- **Claude Code:** `CLAUDE.md` v repu shrnuje pravidla. Globální pasti pasma jsou v uživatelském CLAUDE.md.

## Kontrola po změně

```
build.cmd                                  rem překlad, velikost, volné místo (teď asi 5 KB)
python tools\emu\port.py 4000 build\x.png  rem port v SAPIemu 4 s, snímek CGA-1V (prohlédnout)
python tools\emu\ay_check.py 300 AEFR-     rem hudba: registry AY portu proti modelu (výběr kláves)
python tools\emu\bench.py                  rem čas snímku při 4 a 2 MHz, zpožděné snímky
python tools\emu\block_check.py 100        rem barevné bloky ve scrolleru (chyba palety)
python tools\emu\crash_check.py           rem všech 27 skladeb po 20 s, hlídá pád (PC mimo program)
build.cmd diag                             rem build\fxs4diag.com: za běhu nekreslí (hledání sněžení na HW)
```

Po změně disassembleru (`tools/annot.py`): `python tools\mkdis.py asm orig\fxs4.asm` a `python
tools\check_orig.py` (musí hlásit OK). `sapi/fxs4_sapi.asm` se tím nemění, změny v něm jsou ruční.

**Sněžení se v emulátoru neprojeví**, změny kolem palety a zakázaného přerušení musí autor ověřit na HW.

## Vydání nové verze

1. Popsat změny v `docs/release-notes/vX.Y.Z.md` (vzor `v1.0.0.md`), upravit verzi v `README.md` a stav zde.
2. `build.cmd`, commit, `git push`.
3. `git tag vX.Y.Z` a `git push origin vX.Y.Z`.
4. `gh release create vX.Y.Z build\fxs4.com build\fxs4.hex --title "SAPI-FXS4 X.Y.Z" --notes-file
   docs\release-notes\vX.Y.Z.md`.

## Rozhodnutí autora

- **Napodobit funkci, ne Spectrum.** Obraz se kreslí přímo na CGA-1V, „na první pohled podobný“. Žádné buffery
  ve formátu Spectra, věrné atributy ani jejich kolize. Hudba ale musí hrát přesně jako originál (registry
  AY tick po ticku).
- **Scroller:** plynulý posun 2 body za snímek (varianta 1b). Duha přebíhá přes text o písmeno za snímek
  (posun palety). Barvy písmen samy o sobě jako v originálu nejsou.
- **SPACE:** po novém startu animace se oblast animace vymaže. Na Spectru staré čáry zůstávaly.
- **Skrytá 27. skladba** (A4A6h, na Spectru bez klávesy) je na klávese `-`.
- **Hlavní cíl je 4 MHz** (sestava V má TURBO), 2 MHz má fungovat taky (stíhá, animace je pomalejší).
- Klávesnice se čte v přerušení 1300 Hz, protože Consul 262.3 na JPR-1V nemá 7474 (STROBE je pulz 1 ms).
- Paleta CGA-1V se mění jen v zatemnění a přerušení nesmí být dlouho zakázané (jinak na HW „sněží“).

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
| 3498458 | dokumentace: README, `docs/SOUHRN.md`, `docs/vyvoj.md` |
| 4ebca60 | paleta jen v zatemnění CGA-1V (sněžení na HW), diagnostická verze |
| aa78a16 | bez `DI` ve `frame_play` (sněžení nahoře při mačkání ENTER) |
| tag v1.0.0 | vydání 1.0.0 |
| 4a76fe4 | vlastní zásobník rychlého přerušení: skladba D padala |
| tag v1.0.1 | vydání 1.0.1 |

## Ověřeno na HW (2026-10-07, autor)

- Port na skutečné sestavě V funguje: obraz CGA-1V v režimu EGA s paletou po pásech, přerušení z MPH-1V na
  1300,7 Hz, klávesnice, zvuk YM3812.
- **Paleta Bt476 se smí měnit jen v zatemnění.** Zápisy během kreslení dělaly „sníh“ po celé obrazovce. Port ji
  zapisuje, když STATUS CGA-1V hlásí zatemnění (D7). Diagnostická verze, která za běhu nekreslí do videoram
  (`build.cmd diag`), nesněžila taky, takže přístupy CPU do videoram obraz neruší.
- **Přerušení nesmí být dlouho zakázané.** S `DI` ve `frame_play` (tiknutí navíc s ENTER) přišlo přerušení na
  zatemnění pozdě a při mačkání ENTER lehce sněžilo nahoře. Bez `DI` nesněží.

## Další kroky a nápady

- Zvuk: jen když bude autor chtít jinou barvu tónu nebo šumu. Nápady jsou šum přes rytmický režim YM3812
  nebo jiná křivka hlasitosti AY. Všechno je v `opl_update` a `ym_regs` (`sapi/platform.asm`).
- 2 MHz: animace čar je pomalejší (10,4 čáry/s proti 18,4 na Spectru). Zrychlit by šla `plot_xor`
  (rychlejší výpočet adresy bodu, například tabulky zarovnané na stránky).

## Nejasnosti

- **Zamrzání u Libora Lasoty (2026-10-08).** Sestava: AND-1V na F800h (MAP1 = L), DGD-1V na C000h (MAP1 = H,
  MAP2 = L), CGA-1V na C000h (MAP1 = MAP2 = H), DSM-1V 10h, MPH-1V 50h, ZRD-1V 60h, RAM-1V (okno 2 KB na F800h
  při MAP1 = L, 16 KB na C000h při MAP1 = H), JPR-1V.
  - FXS4 se mu brzy po startu sekne. Bez DGD-1V to chvíli jede, bez všech grafik déle. Jednou se systém sekl
    i jen s AND-1V.
  - **Liborova hypotéza:** klopný obvod WAIT/READY grafických karet (od AND-1Z) nuluje jen /IOR, /IOW a /RES,
    ne INTA. JPR-1V dává STSTB i při INTA (ne při refreshi). Když přijde INT s adresou v oblasti karty, nebo
    v IM 2 při čtení vektoru z I × 256 s I ≥ C0h, karta nastaví RDY a nikdo ho neshodí. Doporučuje
    ohraničit přístupy na grafiku DI/EI, když je MAP1 aktivní, a hlídat, aby I neukazoval od C0h výš.
  - **Rozbor FXS4:**
    - IM 1 (vektor se nečte) a od verze po 1.0.1 výslovně I = 0 (`sapi_init`; dřív zůstával z CP/M,
      v SAPIemu 00h);
    - všechen kód (0100–9F2Eh) i zásobníky (B300–B6FFh, `isr_stack`, zásobníky kanálů v programu) jsou pod
      C000h, takže adresa PC při INTA ani zápis návratové adresy nikdy nepadnou do karty, i když je MAP1 = H
      celou dobu;
    - DI/EI kolem přístupů na CGA by podle tohoto mechanismu nepomohlo a delší DI nejde: rychlé přerušení
      čte klávesnici a zapisuje paletu v zatemnění (jinak sněží);
    - `OUT 63h,C0h` dává MAP1 = MAP2 = H, takže DGD-1V by měla být odpojená. **Předpoklad:** RAM-1V má MAP1
      a MAP2 na bitech 6 a 7 portu 63h jako `sapi1v.sapi`.
  - **Zjistit od Libora:** nastavení MAP na RAM-1V (port, bity MAP1 a MAP2) a jestli FXS4 zamrzá i s jedinou
    grafickou kartou CGA-1V (pak by šlo o jiný problém než INTA).
- Klávesnice Consul 262.3 bez 7474: čtení STROBE každých 0,77 ms se v praxi zatím neprojevilo ztracenými
  stisky (sledovat).
- Originál na 48K s interfacem Melodik: podle kódu hraje (jen porty FFFDh a BFFDh, 7FFDh ne). V emulátoru
  Spectaculator hraje na 128K i na 48K s Melodikem (ověřil autor), na skutečném HW to ověřené není. Na port
  to vliv nemá.
