# SAPI-FXS4

Port **Fuxoft Soundtrack IV** (František Fuka, ZX Spectrum, 26 skladeb pro AY-3-8912) na Tesla SAPI-1,
sestavu V (JPR-1V, RAM-1V, CGA-1V, MPH-1V), jako CP/M `.COM`.

## Stav

- Originál: `Demos/FXSOUND4.TAP`.
- Hotový disassembler originálu: `orig/fxs4.asm`. Přeloží se bajt po bajtu stejně jako blok CODE
  (744Ah–FFFFh).
- Model přehrávače `tools/player.py` je ověřený v emulátoru zx84. Všech 27 skladeb dává na
  15 000 tiknutích (5 minut) stejné registry AY jako originál.
- **Port běží v SAPIemu** (release 0.2.0-alpha, `machines/sapi1v.sapi`, 4 MHz).
  - Obrazovka je stejná jako na Spectru: rámeček, animace čar s cyklováním barev, texty, VU metry
    a barevný scroller.
  - Přehrávač dává tick po ticku stejné registry AY jako model (ověřeno `tools/emu/ay_check.py` na
    skladbách A, E, F, R, Z a výběrem kláves).
  - Klávesy A–Z vybírají skladbu, ENTER zrychluje, ESC vrací do CP/M.
  - Při 2 MHz práce snímku nestačí (viz Port, Časování).
  - Zvuk YM3812 je první návrh převodu z AY, čeká na poslech.
  - Na skutečném HW zatím nevyzkoušeno.

## Soubory

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
| `sapi/platform.asm` | náhrada Spectra: CGA-1V, 82C54, klávesnice, PLOT a DRAW z ROM, AY → YM3812 |
| `sapi/tables.asm` | generuje `tools/make_tables.py` (needitovat): počáteční obrazovka, adresy řádků CGA, barvy, řádek 23 |
| `tools/zx_start_screen.bin` | kopie zachycené obrazovky pro `make_tables.py` (překlad nepotřebuje zx84) |
| `tools/check_port.py` | po překladu: velikost, program musí končit pod bufferem obrazovky |
| `tools/emu/sapimcp.py`, `port.py` | klient MCP SAPIemu, start portu v CP/M a snímek CGA-1V |
| `tools/emu/ay_check.py` | registry AY portu v SAPIemu proti `player.py` |
| `tools/emu/bench.py` | doba práce snímku po částech při 4 a 2 MHz |

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

### Spuštění

- **Překlad:** `build.cmd` → `build\fxs4.com`, `build\fxs4.hex` (od 0100h), `build\fxs4.sym`. Na konci vypíše
  počet stránek pro `SAVE` (teď 158).
- **V SAPIemu:** v CP/M Soubor → Nahrát program do paměti (`build\fxs4.hex`), pak `SAVE 158 FXS4.COM`. Přes
  MCP: `load_binary` souboru `fxs4.com` na 0100h a `set_registers` s `pc` = 0100h (`tools/emu/port.py`).
- **Ovládání:** A–Z skladba (27. skladba na klávesu nemá), ENTER zrychlení (3 tiknutí za snímek), ESC návrat
  do CP/M.

### Paměť (SAPI)

| Adresa | Obsah |
|---|---|
| 0038h | `JP isr` (původní 3 bajty se při návratu do CP/M vrátí) |
| 0100h | `JP sapi_init`, pak celý originál (744A–FFFFh) přeložený od 0103h, bez tabulky IM 2 a nepoužitých mezer |
| konec originálu | `platform.asm`, `tables.asm`, program končí pod A000h (`tools/check_port.py`) |
| A000–BAFF | obrazovka Spectra `zx_screen` (rozložení 4000–5AFFh, zarovnaná na 800h) |
| BB00–BBFF | konce čar animace (`LINE_BUF`, originál 5B00h) |
| BC00–BCFF | kódy barev řádku (`ZX_CODES`) |
| BD00–BFFF | zásobník |
| C000–FFFF | CGA-1V (`OUT 63h,C0h`), CP/M pod ní se za běhu nevolá |

- Všechny adresy originálu jsou návěští (disassembler je symbolický), proto se celý originál přeložil od 0103h.
  Zbylé pevné adresy jsou jen obrazovka Spectra (`zx_screen+...`) a `LINE_BUF` (začátek stránky, kód
  používá `inc l`).
- Porty: 01h, 02h klávesnice (JPR-1V), 50h–57h MPH-1V (82C54, IEN, IACK, YM3812), 63h MAP. Port FEh
  (border) se nepoužívá.

### Jak je port udělaný

| Spectrum | SAPI-1 V |
|---|---|
| BASIC: zavaděč, obrazovka, smyčka `RANDOMIZE USR 33890` | `sapi_init`: obrazovka ze `start_screen`, `POKE` z ř. 9500–9600, `USR 49500`, smyčka `call lines` |
| obrazovka 4000h, atributy | buffer `zx_screen` + CGA-1V v režimu EGA (4 body a 4bitový kód barvy v bajtu) |
| barva bodu = INK (papír je všude černý) | kód = BRIGHT × 8 + INK, paleta: pás × 32 + kód × 2 + bod |
| výplň atributů řádků 0–15 (cyklování barev animace) | jedna položka palety (kód 8) v pásech 0–4 (`anim_colour`) |
| ROM PLOT-SUB, DRAW-LINE (OVER 1) | `zx_plot`, `zx_draw_line`: stejný algoritmus, XOR do bufferu i do CGA |
| `ei`, `halt` před kreslením čáry | `wait_frame` (přerušení je tu rychlejší) |
| IM 2 na 50 Hz, ROM přerušení (FRAMES, klávesnice) | 82C54 čítač 2, 1300,7 Hz (`isr`): klávesnice, každé 26. přerušení snímek (50,03 Hz) |
| KEY-SCAN | `key_scan`: kód klávesy, která je „dole“ (5 snímků, ENTER 30) |
| AY: R13–R0 na FFFDh/BFFDh (`ay_write`) | `opl_update`: YM3812 kanály 0–2 tóny, 3 šum |
| ROM 0000–0026h jako efekt výšky (skladby E, F, R) | `rom_head` (kopie 64 bajtů ROM) |
| `ld (0000h),a` z dat skladby Y | `ld (song_mark),a` |

### Obraz

- CGA-1V v režimu EGA: bajt = 4 body (D7..D4) + kód barvy (D3..D0) pro ty čtyři. Index barvy = pás (řádek CGA
  / 32) × 32 + kód × 2 + bod. Obrazovka Spectra je uprostřed: 4 řádky shora, 8 bajtů (32 bodů) zleva.
- Atributy v programu jsou jen 00h, 07h, 46h, 41h–47h a cyklování 42h–47h (změřeno v zx84), papír je vždy
  černý. Kód barvy je proto BRIGHT × 8 + INK a paleta má v každém pásu bod 0 černý, bod 1 barvu kódu.
- **Animace (řádky 0–15):** originál každý průchod vyplní 512 atributů jednou barvou. Tady mají tyto řádky kód 8
  a mění se jen jeho barva v paletě (pásy 0–4, kód 8 jinde není).
- **Scroller (řádek 23):** originál posouvá atributy o sloupec za snímek a do sloupce 30 dává další barvu
  (41h–47h, perioda 7). Barva sloupce c je tedy barva sloupce 30 před 30 − c snímky. Sloupec c má pevný kód
  9 + c mod 7 a těchto 7 kódů dostává v paletě (pásy 5 a 6) barvy sloupců 24–30. Výsledek je na obrazovce
  stejný. Sloupce 0 a 31 mají INK 0, nevidí se, kopírují se jen sloupce 1–30 (`r23_line`, rozvinutý kód).
- **VU metry** píšou přímo do CGA a mění jen řádky mezi starou a novou výškou sloupce (`vu_cga`).
- Počáteční obrazovka (rámeček, nápis, texty) je zachycená z originálu v zx84 při `USR 49500`
  (`tools/zx/capture_screen.py`), v portu RLE 2402 bajtů.

### Časování

- Přerušení 1300,7 Hz (0,77 ms) kvůli klávesnici Consul 262.3 bez 7474 (STROBE je pulz 1 ms). Snímek
  originálu je každé 26. přerušení a běží s povoleným přerušením. Když snímek přijde, zatímco předchozí
  ještě běží, dožene se jen jeho tiknutí přehrávače (`ticks_owed`): hudba nezpomalí.
- Práce snímku (`tools/emu/bench.py`, takty 4 MHz):

| Část | Takty |
|---|---|
| VU metry | asi 800 |
| scroller (posun 2 × 8 × 31 RL rozvinutý, atributy, znak) | 11 300 |
| přehrávač (tiknutí) | 3 900 |
| YM3812 (`opl_update`, i návraty) | 8 900 |
| řádek 23 do CGA s paletou | 25 400 |
| **celkem** | 4 MHz: 13,3 ms z 20 ms; 2 MHz: 29 ms (snímky se zpožďují, hudba drží tempo) |

- Originál na Spectru potřeboval na snímek asi 27 000 taktů (7,7 ms při 3,5 MHz). Zbytek času dostává animace
  čar. Jeden bod čáry stojí v portu asi 330 taktů, v ROM podle odhadu z kódu asi 430.

### Zvuk (AY-3-8912 → YM3812)

- Tón AY: 1,7734 MHz / 16 / P = 110 837,5 / P Hz, stejná konstanta jako PSG MZ-800 ve Flappy (`ym_fnum`).
  F-number = K / (P << blok), K = 23ABECh. Perioda pod 18 (nad 6 kHz) mlčí.
- Barva tónu: modulátor se zpětnou vazbou (bzučivý jako obdélník), nosná držená (jako Flappy).
- Šum: jeden generátor pro všechny kanály. Kanál 3 YM3812 (modulátor ×15, zpětná vazba 7) dostane frekvenci
  110 837,5 / periody šumu (nad hranicí YM3812 hraje na maximu) a hlasitost nejhlasitějšího kanálu se
  zapnutým šumem.
- Tón i šum na jednom kanálu (AY dává tón AND šum): tón o 6 dB slabší.
- Hlasitost 0–15 → TL po 3 dB (0 = klíč vypnutý). Hardwarovou obálku AY skladby nepoužívají.
- YM3812 se zapisuje jen při změně a `opl_update` nedělá nic, když se R0–R10 nezměnily.
- Je to přibližné a čeká to na poslech: `build\port_song_A.wav` (20 s skladby A z SAPIemu).

## Poznámky pro port (původní rozbor)

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

## Nejasnosti k ověření na HW

- CGA-1V v režimu EGA (CONFIG D2 = 0, COLMASK FFh) s paletou po pásech 32 řádků a změnami palety za běhu.
- Přerušení F2 z MPH-1V přes /INT0 na JPR-1V v IM 1 (RST 38h) na 1300,7 Hz, potvrzení IACK (`OUT 55h,80h`).
- Klávesnice Consul 262.3 bez 7474: stačí čtení STROBE každých 0,77 ms?
- Rychlost a zvuk na skutečné desce (YM3812: 3,3 µs po adrese, 23 µs po datech).

- Hraje originál na 48K s interfacem Melodik? Podle kódu ano: používá jen porty FFFDh a BFFDh, 7FFDh ne.
  V emulátoru Spectaculator hraje na 128K i na 48K s Melodikem (ověřil autor). Na skutečném HW to ověřené není.
  Na port to vliv nemá.
