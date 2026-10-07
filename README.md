# SAPI-FXS4

Port **Fuxoft Soundtrack IV** (František Fuka, ZX Spectrum, 26 skladeb pro AY-3-8912) na Tesla SAPI-1,
sestavu V (JPR-1V, RAM-1V, CGA-1V, MPH-1V), jako CP/M `.COM`.

## Stav

- Originál: `Demos/FXSOUND4.TAP`.
- Hotový disassembler originálu: `orig/fxs4.asm`. Přeloží se bajt po bajtu stejně jako blok CODE
  (744Ah–FFFFh).
- Model přehrávače `tools/player.py` je ověřený v emulátoru zx84. Všech 27 skladeb dává na
  15 000 tiknutích (5 minut) stejné registry AY jako originál.
- Port zatím nezačal.

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
```

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

## Poznámky pro port

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

- Hraje originál na 48K s interfacem Melodik? Podle kódu ano: používá jen porty FFFDh a BFFDh, 7FFDh ne.
