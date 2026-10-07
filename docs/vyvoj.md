# SAPI-FXS4: vývoj

Technické podrobnosti k portu Fuxoft Soundtrack IV na SAPI-1: nástroje, rozbor originálu, jak je port
udělaný a jak se ověřuje. Stav, postup na novém počítači a rozhodnutí jsou v `docs/SOUHRN.md`, pro
uživatele je `README.md`.

## Soubory a nástroje

| Soubor | Obsah |
|---|---|
| `orig/fxs4.asm` | disassembler originálu, generuje ho `tools/mkdis.py`, needitovat |
| `tools/annot.py` | anotace: vstupní body, jména, komentáře, datové oblasti, seznam skladeb |
| `tools/mkdis.py` | generátor: rekurzivní sestup kódem, rozložení dat skladeb podle `player.py` |
| `tools/player.py` | model přehrávače v Pythonu: rozložení dat skladeb, záznam registrů AY po tiknutích |
| `tools/z80dis.py` | dekodér Z80 (převzatý ze SAPI-Flappy) |
| `tools/check_orig.py` | přeloží `orig/fxs4.asm` pasmem a porovná ho s TAP |
| `tools/zx/zx84.py` | klient MCP emulátoru zx84 přes stdio (`..\zx84`, potřebuje Node.js a `npm install`) |
| `tools/zx/boot.py` | spustí originál v zx84: 128K, 48 BASIC, `LOAD ""`, ENTER |
| `tools/zx/ay_compare.py` | registry AY originálu v zx84 proti `player.py`, tick po ticku |
| `tools/zx/exec_trace.py` | provedené adresy originálu v zx84 do `build/exec_zx84.txt` (čte `mkdis.py`) |
| `tools/zx/capture_screen.py` | obrazovka originálu při startu hudby (`USR 49500`) → `build/zx_start_screen.bin` |
| `sapi/fxs4_sapi.asm` | port: kopie `orig/fxs4.asm` se změnami `SAPI:`, dál se edituje ručně |
| `sapi/platform.asm` | funkce Spectra na SAPI: obraz na CGA-1V, 82C54, klávesnice, AY → YM3812 |
| `sapi/tables.asm` | generuje `tools/make_tables.py` (needitovat): obrazovka pro CGA, adresy linek, barvy, F-number |
| `tools/zx_start_screen.bin` | kopie zachycené obrazovky pro `make_tables.py` (překlad nepotřebuje zx84) |
| `tools/check_port.py` | po překladu: velikost, program musí končit pod zásobníkem (`PROGRAM_LIMIT`) |
| `tools/emu/sapimcp.py`, `port.py` | klient MCP SAPIemu, start portu v CP/M a snímek CGA-1V |
| `tools/emu/ay_check.py` | registry AY portu v SAPIemu proti `player.py` |
| `tools/emu/bench.py` | doba práce snímku po částech při 4 a 2 MHz |
| `tools/emu/block_check.py` | hledá barevné bloky ve scrolleru na snímcích CGA-1V (chybná položka palety) |

Příkazy (Python 3, pasmo v `E:\SAPI_GIT\Tools\pasmo-0.5.3\pasmo.exe` nebo v proměnné `PASMO`):

```
python tools\mkdis.py asm orig\fxs4.asm     rem po změně annot.py
python tools\check_orig.py                  rem překlad a porovnání s originálem
python tools\mkdis.py report                rem konflikty, operandy brané jako adresy nebo čísla
python tools\mkdis.py map                   rem úseky kódu a dat
python tools\player.py cover                rem přehraje všechny skladby, hlásí konflikty v datech
python tools\player.py log A 500            rem registry R0-R13 skladby A po tiknutích (50 Hz)
python tools\zx\ay_compare.py 15000         rem všech 27 skladeb v zx84 proti modelu (asi 4 min)
python tools\zx\ay_compare.py 500 AB --save rem jen A a B, registry z zx84 do build\ay_A.txt ...
python tools\zx\exec_trace.py               rem provedené adresy, pak znovu mkdis.py asm a report
build.cmd                                   rem port: build\fxs4.com, .hex, .sym
python tools\emu\port.py 4000 build\x.png   rem port v SAPIemu 4 s, snímek CGA-1V
python tools\emu\ay_check.py 300 AEFR       rem registry AY portu proti modelu
python tools\emu\bench.py                   rem doba práce snímku
```

Skripty v `tools/emu` potřebují `sapiemu-cli --machine machines/sapi1v.sapi --mcp --mcp-port 8592` spuštěný
na pozadí ve složce `..\SAPIemu-release` (jiný port: proměnná `SAPIEMU_MCP`). Release je oddělený od vývojové
verze SAPIemu, která se mezitím může překládat, a má vlastní disk C:. Skripty si nabootují CP/M (volba 1)
a uloží stav `cpm` do paměti emulátoru.

zx84 nahrává pásku hned po resetu. `boot.py` proto vyrobí `build/fxs4_boot.tap`, v němž je před
originálem prázdný blok (1500 B). Pásek se tak nedostane k originálu dřív, než se projde menu 128K
a napíše `LOAD ""`. Skladby se v zx84 spouštějí klávesou. 27. skladba se spustí tak, že se během stisku
Y dočasně přepíše operand na C0EDh.

## Originál

### Zavaděč (BASIC)

- **Ř. 9000:** kontrola 48K režimu. Při `PEEK 23388` ≠ 0 vypíše „PREPNETE PROSIM SPECTRUM DO 48K MODU“.
  Pak `CLEAR 26999`, `CHARS` = 8060h (font na 8160h) a nahrání kódu.
- **Ř. 9200 a 9500:** úvodní obrazovka, `POKE` na 84E9h a 8501h.
- **Ř. 9600:** spustí hudbu (`USR 49500`).
- **Ř. 20:** smyčka `RANDOMIZE USR 33890` (animace čar).
- **Ř. 9240:** kopírování programu na kazetu.

### Paměť

| Adresa | Obsah |
|---|---|
| 744A–815F | rolující text (velká písmena znamenají písmena s diakritikou), FFh = konec |
| 8160–845F | font znaků 20h–7Fh |
| 8462–85D3 | animace čar (`lines`, kreslí ROM `DRAW`, konce čar v bufferu tiskárny 5B00h), náhodná čísla |
| 85D4–BFFF | data skladeb Y, X, W, Z, V, U, T, S, R, Q, P, O, N, M a skryté 27. skladby (A4A6h) |
| C000–C15B | práce v přerušení: klávesy skladeb, tabulka kláves → skladba (`song_for_key`) |
| C15C–C18C | vstupy: start hudby, přerušení (`isr_body`: VU metry, scroller, `frame`) |
| C200–C301 | tabulka vektorů IM 2 (I = C2h, všechny FFh) |
| C350–C358 | skokové vektory: start skladby, stop, tiknutí |
| C359–C3E5 | start skladby, obsluha IM 2, stop |
| C3E6–C543 | proměnné, stínové registry AY, zásobníky kanálů, bloky kanálů, tabulka tónů |
| C544–C834 | přehrávač: tiknutí, kanál, obálka, efekt výšky, příkazy 80h–8Eh |
| C835–C83A | hlavička právě hrané skladby |
| C83C–FEC3 | data skladeb A–L |
| FEC4–FF27 | VU metry (`vu_meters`) a tabulka jejich adres na obrazovce, ukazatele textu |
| FF28–FF94 | scroller v řádku 23 (2 body za snímek, každé 4 snímky nový znak) |
| FFF3–FFFF | čítač scrolleru, `jp isr` na FFF4h a `jr` na FFFFh, zapisuje je start skladby |

### Běh

- **Přerušení (50 Hz):**
  - FFFFh (`jr`) → FFF4h (`jp isr`) → VU metry, scroller, `frame` → `jp 0038h` (ROM).
  - `frame` přečte klávesnici. Klávesa skladby ji spustí znovu od začátku, jinak proběhne jedno tiknutí
    přehrávače, se stisknutým ENTER tři.
  - Během tiknutí je border fialový.
- **Hlavní program:** BASIC mezitím volá animaci čar.

### Přehrávač

- **Výstup do AY:**
  - Každé tiknutí zapíše všech 14 registrů R13 až R0 ze stínové kopie `ay_regs` (C3E6h) přes porty
    FFFDh a BFFDh (`ay_write`).
  - R11–R13 (hardwarová obálka) nic nemění, v TAP jsou 0. Hlasitosti v R8–R10 nemají v žádné skladbě
    bit 4 (ověřeno `player.py`), takže hardwarová obálka AY se nepoužívá. Hlasitost řídí přehrávač sám
    (obálky hlasitosti v datech).
  - Noise je jeden pro všechny kanály. Mixer (R7) skládá bity kanálů (`+3`, výchozí 8 = tón bez šumu).
- **Kanály:** každý kanál má 20 B (`chan_a/b/c`) a vlastní zásobník 32 B (`stack_a/b/c`).
  - Zásobník slouží pro volání a smyčky v datech.
  - Přehrávač ho používá tak, že při tiknutí kanálu nastaví SP na zásobník kanálu.
- **Formát dat:** v hlavičce `tools/player.py`.
  - Hlavička skladby jsou 3 ukazatele na proudy not kanálů A, B, C.
  - V proudu jsou noty, pauzy a příkazy: skok, volání, smyčka, šum, mixer, obálka hlasitosti, efekt výšky,
    transpozice, legato a volání strojového kódu.
- **Šum:** maska příkazu 8Dh je 0Fh pro skladby A–K a 1Fh pro L–Z (`song_for_key`, `set_noise_mask`).
- **Strojový kód v datech:**
  - Příkaz 8Ch skladby Y volá 86AEh a 86AAh: `ld (0000h),a` s A = 1 nebo 2.
  - Na Spectru je na 0000h ROM, takže zápis nic nedělá.
  - Na SAPI je na 0000h RAM (CP/M), port to musí ošetřit.
- **ROM jako efekt výšky:**
  - `init_song` nuluje začátek efektu výšky (`+16/17`). Kanál, který nedostane příkaz 86h, proto čte
    jako efekt výšky ROM od 0000h. Na začátku každé noty začne znovu od 0000h.
  - Týká se to skladeb E, F a R. Čtou se bajty 0000–0026h, které jsou stejné v ROM 48K i v ROM 1
    modelu 128K.
  - `player.py` je má v `ROM_HEAD`. Port je potřebuje jako data a začátek efektu musí ukazovat na ně.

### Jak vznikl disassembler

- **Kód:** rekurzivní sestup z `ENTRIES` v `annot.py`. Patří k nim i obsluhy příkazů 80h–8Eh, které se
  volají přes tabulku skoků a `push`/`ret`.
  - Ověřeno záznamem z zx84 (`exec_trace.py`, `mkdis.py` ho čte z `build/exec*.txt`).
  - Provedlo se 837 adres a všechny jsou v disassembleru jako kód.
  - Z 849 instrukcí se v krátkém scénáři neprovedlo 14:
    - přetečení ukazatelů (náhodná čísla 85B6h, konec textu FF72h),
    - druhá značka skladby Y (86AAh),
    - mrtvá druhá položka klávesy T (C0F4h),
    - nepoužitý vektor `jp_tick`,
    - příkaz skoku 80h.
  - FFF4h a FFFFh jsou v obrazu data, kód tam zapíše až `init_song` (`DATA_FORCE`).
- **Data skladeb:**
  - `player.py` přehraje 30 000 tiknutí každé skladby (všech 27) a zaznamená, který bajt se čte jako
    nota, obálka nebo efekt.
  - Při 20 000 i 60 000 tiknutích je to stejných 28 055 bajtů a konflikty nejsou.
  - Bajty, které se nikdy nečtou, jsou většinou koncové skoky `80 w` za obálkami s dlouhou poslední
    hodnotou a nepoužité obálky. `mkdis.py` je projde staticky a ve výpisu je označí „never reached“.
  - Všechny ukazatele v datech skladeb jsou tak návěští (`nt_`, `env_`, `fx_`, `song_X`). Data jde
    přestěhovat.
  - Nejasný zůstal jen úsek 9CBBh (4 B, přehrávač ho nečte).
- **Samomodifikace:** operandy, které program přepisuje, mají návěští `equ $-n`:
  - `lines_colour_ptr`, `random_rom`, `random_seq`, `noise_mask_val`, `noise_mask`;
  - `lines_exit_jp` (BASIC mění operační kód).

## Port (SAPI-1 V)

Port napodobuje, **co program dělá**, ne hardware Spectra. Hudba (přehrávač a data skladeb) je originál beze
změny, obraz se kreslí přímo na CGA-1V vlastními rutinami.

- **Překlad:** `build.cmd` → `build\fxs4.com`, `build\fxs4.hex` (od 0100h), `build\fxs4.sym`. Napřed
  `tools/make_tables.py` (vygeneruje `sapi/tables.asm`), na konci `tools/check_port.py` (velikost, volné
  místo, počet stránek pro `SAVE`).
- **Diagnostika sněžení:** `build.cmd diag` → `build\fxs4diag.com`, `.hex` (`--equ DIAG=1`). Za běhu nic
  nekreslí: VU metry, scroller, čáry ani mazání animace. Zůstane počáteční obrazovka, hudba a změny palety
  v zatemnění.
- **Zdroj portu:** `sapi/fxs4_sapi.asm` vznikl jednou z `orig/fxs4.asm` a dál se edituje ručně. Každá změna
  je označená `SAPI:` a říká, co dělal originál.

### Paměť (SAPI)

| Adresa | Obsah |
|---|---|
| 0038h | `JP isr` (původní 3 bajty se při návratu do CP/M vrátí) |
| 0100h | `JP sapi_init`, pak originál (744A–FFFFh) přeložený od 0103h, bez tabulky IM 2, nepoužitých mezer, VU metrů a scrolleru |
| konec originálu | `platform.asm`, `tables.asm`, program končí pod `PROGRAM_LIMIT` B300h (`tools/check_port.py`) |
| B300–B6FF | zásobník |
| B700–B7FF | konce čar animace (`LINE_BUF`, originál 5B00h, kód používá `inc l`) |
| B800–BFFF | pásy scrolleru A a B (8 linek × 128 bajtů) |
| C000–FFFF | CGA-1V (`OUT 63h,C0h`), CP/M pod ní se za běhu nevolá |

- Všechny adresy originálu jsou návěští (disassembler je symbolický), proto se originál přeložil od 0103h.
- Porty: 01h, 02h klávesnice (JPR-1V), 50h–57h MPH-1V (82C54, IEN, IACK, YM3812), 63h MAP. Port FEh
  (border) se nepoužívá.

### Jak je port udělaný

| Spectrum | SAPI-1 V |
|---|---|
| BASIC: zavaděč, obrazovka, smyčka `RANDOMIZE USR 33890` | `sapi_init`: obrazovka `cga_screen`, `POKE` z ř. 9500–9600, `USR 49500`, smyčka `call lines` |
| obrazovka 4000h s atributy | CGA-1V v režimu EGA (4 body a 4bitový kód barvy v bajtu), kreslí se do ní přímo |
| výplň atributů řádků 0–15 (cyklování barev animace) | jedna položka palety (kód 8) v pásech 0–4 (`anim_colour`) |
| ROM PLOT-SUB, DRAW-LINE (OVER 1) | `plot_xor`, `draw_xor`: stejný algoritmus čáry, XOR rovnou v CGA |
| `ei`, `halt` před kreslením čáry | `wait_frame` (přerušení je tu rychlejší) |
| VU metry (FEC4h) | `vu_cga`: stejné sloupce, mění se jen řádky mezi starou a novou výškou |
| scroller (FF28h) | `scroll_cga`: plynule 2 body za snímek, duha přes paletu (o písmeno za snímek) |
| IM 2 na 50 Hz, ROM přerušení (FRAMES, klávesnice) | 82C54 čítač 2, 1300,7 Hz (`isr`): klávesnice, každé 26. přerušení snímek (50,03 Hz) |
| KEY-SCAN | `key_scan`: kód klávesy, která je „dole“ (5 snímků, ENTER 30): písmena, ENTER, SPACE, `-` (28h, 27. skladba), ostatní jako 0 |
| BASIC ř. 20 po SPACE: animace znovu, staré čáry zůstanou | `main_loop`: `anim_clear` (čistý rámeček) a animace znovu |
| AY: R13–R0 na FFFDh/BFFDh (`ay_write`) | `opl_update`: YM3812 kanály 0–2 tóny, 3 šum |
| ROM 0000–0026h jako efekt výšky (skladby E, F, R) | `rom_head` (kopie 64 bajtů ROM) |
| `ld (0000h),a` z dat skladby Y | `ld (song_mark),a` |

### Obraz

- **CGA-1V v režimu EGA:** bajt = 4 body (D7..D4) + kód barvy (D3..D0) pro ty čtyři. Index barvy = pás (řádek
  CGA / 32) × 32 + kód × 2 + bod. Bod 0 je všude černý, bod 1 má barvu kódu: kód = BRIGHT × 8 + INK jako na
  Spectru (`rgb_table`). Obraz Spectra je uprostřed: 4 řádky shora, 8 bajtů (32 bodů) zleva.
- **Počáteční obrazovka** (rámeček, nápis, texty) je zachycená z originálu v zx84 při `USR 49500`
  (`tools/zx/capture_screen.py`). `tools/make_tables.py` ji při překladu převede na data CGA (`cga_screen`,
  RLE 2154 bajtů).
- **Animace čar:** body se invertují rovnou v CGA (`plot_xor`), algoritmus čáry je stejný jako v ROM (`draw_xor`).
  Oblast animace má kód 8 a cyklování barev mění jeho barvu v paletě (pásy 0–4).
- **Paleta se zapisuje jen v zatemnění CGA-1V** (`pal_flush`).
  - Barva animace (`anim_colour`) a otočení duhy (`scr_rainbow`) se jen poznamenají v `pal_anim`, `scr_rot`
    a `pal_dirty`.
  - Rychlé přerušení (1,3 kHz) čte STATUS CGA-1V (D7 = začátek zatemnění, 60 Hz). Když je nastavený, potvrdí
    ho (CONFIG D7 = 1) a zapíše změny. Zatemnění trvá asi 4 ms (125 řádků), zápis 19 položek se vejde.
  - Důvod: na skutečné CGA-1V obraz „sněžil“ po celé obrazovce. Zápis do RAMDACu během kreslení ruší obraz
    tam, kde je zrovna paprsek.
  - Paletu tak zapisuje jen přerušení, takže dřívější souběh hlavní smyčky s přerušením (adresa a R, G, B jsou
    čtyři zápisy, „čudlíky“ ve scrolleru do a2bc3de) už nastat nemůže. `tools/emu/block_check.py` je hledá
    na snímcích CGA.
- **Scroller:** text jede plynule 2 body za snímek sloupci 1–30 řádku 23, nové písmeno každé 4 snímky.
  - Písmena dostávají po řadě kódy barev 9–15.
  - Každý snímek se barvy těchto kódů v paletě (pásy 5 a 6) posunou o jeden kód (`scr_rainbow`), takže duha
    přebíhá doleva o písmeno za snímek, rychleji než text. Originál posouval barvy o sloupec za snímek.
  - Text je ve dvou pásech jako hotové bajty CGA (s kódem barvy). Pás A má bajt j = body 4j až 4j+3 textu,
    pás B bajt j = body 4j+2 až 4j+5.
  - Snímek jen zkopíruje 60 bajtů každé z 8 linek z pásu A (sudé snímky) nebo B (liché) do CGA (`LDI`
    rozvinuté).
  - Linka pásu je kruh 64 bajtů uložený dvakrát (j a j + 64), takže 60 bajtů od libovolného j je za sebou.
  - Nové písmeno se zapíše do obou pásů 60 bajtů před okno (`scr_char`).
- **VU metry:** stejné sloupce jako originál (bajt 7Eh na řádek, výška = hlasitost kanálu s tónem). Mění se jen
  řádky mezi starou a novou výškou.

### Časování

- Přerušení 1300,7 Hz (0,77 ms) kvůli klávesnici Consul 262.3 bez 7474 (STROBE je pulz 1 ms). Snímek
  originálu je každé 26. přerušení a běží s povoleným přerušením. Když snímek přijde, zatímco předchozí
  ještě běží, dožene se jen jeho tiknutí přehrávače (`ticks_owed`): hudba nezpomalí.
- Práce snímku (`tools/emu/bench.py`, jeden snímek, takty 4 MHz):

| Část | Takty |
|---|---|
| VU metry (jen změny) | asi 200 |
| scroller (kopie 8 × 60 bajtů, písmeno každé 4 snímky) | asi 1 300–9 300 |
| přehrávač (tiknutí) | asi 4 000 |
| YM3812 (`opl_update`, F-number z tabulky) | asi 6 000 |
| **průměr snímku** | 4 MHz: 5,7 ms (nejdelší 7,3 ms) z 20 ms; 2 MHz: 12,6 ms (nejdelší 20,2 ms) |

- Žádný snímek se v 10 s nezpozdí ani při 2 MHz.
- **Animace čar:** při 4 MHz 18,6 nových čar za sekundu, originál v zx84 18,4. Při 2 MHz 10,4.

### Zvuk (AY-3-8912 → YM3812)

- Tón AY: 1,7734 MHz / 16 / P = 110 837,5 / P Hz, stejná konstanta jako PSG MZ-800 ve Flappy.
  F-number = K / (P << blok), K = 23ABECh.
  - Perioda se posouvá doleva (blok), dokud není aspoň 2283. Pak se F-number vezme z `fnum_table`
    (571 hodnot po 4).
  - Perioda pod 18 (nad 6 kHz) mlčí.
- Barva tónu: modulátor se zpětnou vazbou (bzučivý jako obdélník), nosná držená (jako Flappy).
- Šum: jeden generátor pro všechny kanály. Kanál 3 YM3812 (modulátor ×15, zpětná vazba 7) dostane frekvenci
  110 837,5 / periody šumu (nad hranicí YM3812 hraje na maximu) a hlasitost nejhlasitějšího kanálu se
  zapnutým šumem.
- Tón i šum na jednom kanálu (AY dává tón AND šum): tón o 6 dB slabší.
- Hlasitost 0–15 → TL po 3 dB (0 = klíč vypnutý). Hardwarovou obálku AY skladby nepoužívají.
- YM3812 se zapisuje jen při změně a `opl_update` nedělá nic, když se R0–R10 nezměnily.
- Autorovi zní dobře (`build\port_song_A.wav`, 20 s skladby A z SAPIemu).

## Původní rozbor před portem

- **Paměť:**
  - Originál zabírá 744Ah–FFFFh, včetně vektoru IM 2 na FFF4h a FFFFh.
  - Na SAPI je C000–FFFFh za běhu CGA-1V a pod ní je CP/M (viz SAPI-Flappy).
  - Kód i skladby se musí přestěhovat. Data skladeb jsou proto symbolická.
- **Zvuk:** MPH-1V má YM3812 (OPL2), ne AY. Rozhraní je jedno místo: `ay_write` dostává hotové registry
  R0–R13 v každém tiknutí.
- **Časování:** tiknutí je 50 Hz. CGA-1V dává 60 Hz, proto 50 Hz musí dávat 82C54 na MPH-1V.
- **Spectrum v kódu:** ROM (`KEY-SCAN`, `DRAW`, `PLOT`, obsluha přerušení 0038h), systémové proměnné,
  obrazovka a atributy. Animace čar je v BASICu a ROM, port ji musí nahradit.
- **Model přehrávače:** `player.py` dává registry AY po tiknutích stejně jako originál (ověřeno
  `ay_compare.py`) a může sloužit jako reference pro port.
  - Model hraje každou skladbu od stavu uloženého v TAP.
  - V zx84 se skladby hrály po sobě (A, B, …), takže hodnoty, které program přenáší mezi skladbami,
    výsledek neovlivňují.
- **Border:** během tiknutí přehrávače je fialový (měřítko času CPU). Na SAPI nemá obdobu.

## Pasti

- **pasmo:** lokální návěští `.x` jsou globální, unární minus na začátku výrazu neguje celý zbytek (viz
  globální CLAUDE.md). `jr` přes rozvinuté `LDI` (`rept 60`) nedosáhne, je tam `jp`.
- **Paleta CGA-1V** (adresa a R, G, B) se smí z hlavní smyčky zapisovat jen se zakázaným přerušením (viz Obraz).
- **Klávesy:** KEY-SCAN 20h = SPACE, 21h = ENTER. Animace testuje kód + 1 = 21h, tedy SPACE (dřív v komentářích
  omylem ENTER).
- **Stav kanálů z TAP:** bloky kanálů v obrazu obsahují ukazatele z poslední hrané skladby. Žádná skladba je
  nepoužije dřív, než si je nastaví (ověřeno `player.py` s přepsanými hodnotami), proto přesun nevadí.
- **zx84:**
  - `load` resetuje stroj a pustí pásku hned (proto `build/fxs4_boot.tap` s prázdným blokem);
  - adresy v `read_memory` jsou hex řetězce;
  - log pastí drží jen 2000 řádků (`ay_compare.py` čte po 100 snímcích);
  - `trace portio` dává jen souhrn, pořadí zápisů dávají pasti (`trap` s `log`);
  - po zapnutí 48 BASIC je třeba počkat na „© 1982“, jinak se první klávesa ztratí.
- **SAPIemu:**
  - `screenshot` vrací obrázek v odpovědi (base64), soubor neukládá;
  - `cpu_turbo` má parametr `on`;
  - `cycles` počítá takty 4 MHz i při 2 MHz;
  - `read_memory` vrací nejvýš 4096 bajtů;
  - CGA-1V prolíná poslední dva snímky (`frame_blend`), barvy měněné každý snímek proto na snímcích vypadají
    pastelově.
