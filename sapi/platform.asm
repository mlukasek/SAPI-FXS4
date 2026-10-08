; =====================================================================
;  SAPI-1 V platform layer of the Fuxoft Soundtrack IV port: what the
;  Spectrum hardware, ROM and BASIC did, done on the SAPI-1 V.
;
;  Hardware (machines/sapi1v.sapi of SAPIemu):
;  - RAM-1V MAP register 63h: C0h = MAP1 = MAP2 = H, CGA-1V at C000h
;    (RAM C000-FFFF hidden, CP/M is not called while the program runs);
;  - CGA-1V in EGA mode: 80 bytes per line, 4 pixels per byte; the high
;    nibble has the pixels (D7 left), the low nibble a colour code for
;    the four. Colour index = line / 32 * 32 + code * 2 + pixel: pixel 0
;    is black, pixel 1 the colour of the code (BRIGHT * 8 + INK of the
;    Spectrum; code 8 = the colour of the line animation). The picture
;    of the Spectrum is in the middle (CGA_TOP lines, CGA_LEFT bytes);
;  - MPH-1V at 50h: 82C54 counter 2 (CLK 55930.4 Hz) sets F2 -> /INT0
;    (JPR-1V, IM 1 = RST 38h); YM3812;
;  - keyboard on JPR-1V (Consul 262.3 without 7474 or EKL-1): STROBE on
;    P0-IN0 (port 01h, active low), code on P1 (port 02h, inverted).
; =====================================================================

MAPREG:		equ 063h		; RAM-1V MAP register
MAP_CGA:	equ 0C0h		; MAP1 = MAP2 = H
CGA:		equ 0C000h		; CGA-1V base
CGA_SIZE:	equ 16000		; 200 lines x 80 bytes
CGA_CFG:	equ CGA+03FFBh		; CONFIG (write)
CGA_STATUS:	equ CGA+03FFBh		; STATUS (read): D7 = vertical blank since the last acknowledge
CGA_PAL_ADDR:	equ CGA+03FFCh		; Bt476 palette address
CGA_PAL_DATA:	equ CGA+03FFDh		; Bt476 R, G, B
CGA_COLMASK:	equ CGA+03FFEh		; Bt476 pixel mask
CFG_EGA:	equ 000h		; EGA mode, CPU and display page A, no IRQ
ANIM_CODE:	equ 8			; colour code of the line animation

PIT2:		equ 052h		; 82C54 counter 2
PITCW:		equ 053h		; 82C54 control word (write)
MIEN:		equ 054h		; MPH-1V IEN (write)
MIACK:		equ 055h		; MPH-1V IACK (write)
YMADDR:		equ 056h		; YM3812 register address
YMDATA:		equ 057h		; YM3812 data

KSTB:		equ 001h		; P0-IN: D0 = keyboard STROBE (active low)
KDATA:		equ 002h		; P1-IN: key code (inverted)

; Interrupt: 82C54 counter 2 in mode 2 with 43: 55930.4 / 43 = 1300.7 Hz
; (0.77 ms), so a STROBE pulse of 1 ms (Consul 262.3 without 7474) is
; always seen. Every 26th interrupt is a Spectrum frame: 50.03 Hz.
TICK_DIV:	equ 43
FRAME_TICKS:	equ 26
IEN_QUIET:	equ 020h		; gate G2, no interrupt
IEN_RUN:	equ 0A0h		; and the F2 interrupt

; Keys: the SAPI keyboards do not tell when a key is let up. A key is
; down for KEY_HOLD frames, ENTER (3 player ticks per frame while it is
; down) for ENTER_HOLD frames: longer than the delay of an autorepeat.
KEY_HOLD:	equ 5			; 100 ms
ENTER_HOLD:	equ 30			; 600 ms
ZX_ENTER:	equ 021h		; KEY-SCAN codes: ENTER (frame: 3 ticks)
ZX_SPACE:	equ 020h		; SPACE (lines: back to BASIC, see key_frame)
ZX_ZERO:	equ 023h		; 0 (does nothing in the program)
ZX_EXTRA:	equ 028h		; '-': the 27th song (no KEY-SCAN code, song_extra)

; Memory above the program (not in the .COM)
PROGRAM_LIMIT:	equ 0B300h		; the program ends below (tools/check_port.py)
STACK_TOP:	equ 0B700h		; stack down to PROGRAM_LIMIT
LINE_BUF:	equ 0B700h		; line end points (page), was 5B00h
STRIP_A:	equ 0B800h		; scroller strips: 8 lines x 128 bytes each
STRIP_B:	equ 0BC00h

; =====================================================================
; Start, main loop, exit
; =====================================================================

; ---- sapi_init
; Entry from CP/M (0100h). Puts JP isr at 38h, maps the CGA in, sets the
; palette, the YM3812 and the keyboard, draws the start screen, does what
; the BASIC did (lines 9500-9600) and starts the 82C54 interrupt and the
; music (USR 49500).
sapi_init:
	di
	ld sp,STACK_TOP
	ld hl,0038h
	ld de,page0_save
	ld bc,3
	ldir
	ld a,0C3h			; JP isr
	ld (0038h),a
	ld hl,isr
	ld (0039h),hl
	im 1
	xor a				; I = 0: the graphics cards set their RDY flip-flop
	ld i,a				; on STSTB at their address and only I/O cycles
					; clear it; INTA and an IM 2 vector read at I >= C0h
					; may leave it set (L. Lasota). IM 1 reads no vector
					; and all code and stacks are below C000h.
	ld a,MAP_CGA
	out (MAPREG),a
	ld a,CFG_EGA+002h		; CPU page B: clear it too
	ld (CGA_CFG),a
	call cga_clear
	ld a,CFG_EGA
	ld (CGA_CFG),a
	call cga_clear
	call pal_init
	ld a,0FFh
	ld (CGA_COLMASK),a
	call ym_init
	ld a,002h			; keyboard ACK off, buzzer off
	out (KSTB),a
	call cga_unpack
	call scr_init
; What the BASIC did before RANDOMIZE USR 49500 (lines 9500-9600)
	ld a,0CAh			; POKE 34025,202: lines end on SPACE only
	ld (lines_exit_jp),a
	ld a,046h			; POKE 34049,70: colour cycle
	ld (colours_1),a
	ld hl,(text_start)		; POKE 65318/65319: scroll text from the start
	ld (text_ptr),hl
	ld a,007h			; the rows of the animation: INK 7 (CLS)
	call anim_colour
	ld a,0B4h			; counter 2: LSB+MSB, mode 2
	out (PITCW),a
	ld a,TICK_DIV
	out (PIT2),a
	xor a
	out (PIT2),a
	ld a,0C0h			; clear F2 and F1
	out (MIACK),a
	ld a,FRAME_TICKS
	ld (frame_div),a
	ld a,IEN_RUN
	out (MIEN),a
	call start_music		; USR 49500 (enables the interrupt)
	ei
; BASIC line 20: RANDOMIZE USR 33890: GO TO 20. The animation ends on
; SPACE and starts again with an empty list of lines; the Spectrum left
; the old lines on the screen, here the frame is drawn clean first.
main_loop:
	call lines
	call anim_clear
	jr main_loop

; ---- sapi_exit
; Back to CP/M (ESC): silence, interrupt off, page 0 back, CGA unmapped,
; warm boot.
sapi_exit:
	di
	ld sp,STACK_TOP
	ld a,IEN_QUIET
	out (MIEN),a
	ld a,0C0h
	out (MIACK),a
	call ym_silence
	ld hl,page0_save
	ld de,0038h
	ld bc,3
	ldir
	xor a
	out (MAPREG),a
	ld a,002h
	out (KSTB),a
	jp 0

; =====================================================================
; Interrupt
; =====================================================================

; ---- isr (RST 38h, 1300.7 Hz)
; The quick part runs on its own stack (isr_stack): the player of the
; original sets SP to the stack of a channel (32 bytes, deep calls and
; loops in the song data) and runs with interrupts enabled here; on the
; Spectrum its interrupt was the only one. Pushing there overwrote the
; variables below the stack (song D crashed).
; Acknowledges F2, reads the keyboard and writes palette changes when the
; CGA-1V is in its vertical blank. Every FRAME_TICKS interrupts it
; does the work of a Spectrum frame with interrupts enabled (the keyboard
; is read meanwhile): key timers and isr_body of the original (VU meters,
; scroller, keys, player) while music_on. A frame
; that comes while the last one still runs only gets its player tick
; (ticks_owed, played at the end of the running one).
isr:
	ld (isr_sp),sp			; own stack: the player runs with SP in a channel
	ld sp,isr_stack_top		; stack of 32 bytes (song D fills 22 of them)
	push af
	ld a,080h			; clear F2
	out (MIACK),a
	in a,(KSTB)
	rrca
	jr nc,isr_strobe
	ld a,(kbd_state)		; STROBE inactive: ACK off after a key
	or a
	jr z,isr_kdone
	xor a
	ld (kbd_state),a
	ld a,002h
	out (KSTB),a
	jr isr_kdone
isr_strobe:				; STROBE active: take the key once
	ld a,(kbd_state)
	or a
	jr nz,isr_kdone
	inc a
	ld (kbd_state),a
	in a,(KDATA)
	cpl
	ld (kbd_code),a
	ld a,003h			; ACK (EKL-1 waits for it)
	out (KSTB),a
isr_kdone:
	ld a,(CGA_STATUS)		; vertical blank of the CGA-1V (60 Hz)?
	rlca
	jr nc,isr_novbi
	ld a,CFG_EGA+080h		; acknowledge it (CONFIG D7)
	ld (CGA_CFG),a
	ld a,(pal_dirty)		; palette changes now
	or a
	call nz,pal_flush
isr_novbi:
	ld a,(frame_div)
	dec a
	ld (frame_div),a
	jr z,isr_frame
	pop af
	ld sp,(isr_sp)
	ei
	reti
isr_frame:
	ld a,FRAME_TICKS
	ld (frame_div),a
	ld a,(frames)			; FRAMES (5C78h, the ROM counted it)
	inc a
	ld (frames),a
	ld a,(frame_busy)
	or a
	jr z,isr_work
	ld a,(frames_lost)		; diagnostics (tools/emu/bench.py)
	inc a
	ld (frames_lost),a
	ld a,(ticks_owed)		; the running frame plays this tick too
	inc a
	ld (ticks_owed),a
	pop af
	ld sp,(isr_sp)
	ei
	reti
isr_work:				; the work of a frame on the interrupted stack:
	inc a				; the main loop's (a frame never starts during
	ld (frame_busy),a		; the player, that runs in the work of a frame)
	pop af
	ld sp,(isr_sp)
	push af
	push bc
	push de
	push hl
	push ix
	push iy
	ei
	call key_frame
	ld a,(music_on)
	or a
	call nz,isr_body		; (frame_play runs with interrupts enabled too)
frame_end:
isr_owed:				; ticks of the frames that came meanwhile:
	di				; the music does not slow down
	ld a,(ticks_owed)
	or a
	jr z,isr_done
	dec a
	ld (ticks_owed),a
	ei
	ld a,(music_on)
	or a
	call nz,tick
	jr isr_owed
isr_done:
	xor a
	ld (frame_busy),a
	pop iy
	pop ix
	pop hl
	pop de
	pop bc
	pop af
	ei
	reti

; ---- wait_frame
; Wait for the next Spectrum frame (the original did EI, HALT).
; Keeps BC, DE, HL.
wait_frame:
	ei
	push hl
	ld hl,frames
	ld a,(hl)
wf_loop:
	cp (hl)
	jr z,wf_loop
	pop hl
	ret

; =====================================================================
; Keyboard
; =====================================================================

; ---- key_frame
; Once a frame: a new key from the interrupt becomes the key that is
; down (KEY-SCAN code) for KEY_HOLD frames; ESC goes back to CP/M.
; Letters choose songs, ENTER makes the music faster. SPACE ends the line
; animation (lines tests KEY-SCAN code + 1 = 21h), the BASIC starts it
; again with an empty list of lines, so the lines on the screen stay:
; the original does the same.
key_frame:
	ld a,(kbd_code)
	or a
	jr z,kf_hold
	ld c,a
	xor a
	ld (kbd_code),a
	ld a,c
	cp 01Bh				; ESC
	jp z,sapi_exit
	ld b,ENTER_HOLD
	ld e,ZX_ENTER
	cp 00Dh				; CR
	jr z,kf_set
	ld b,KEY_HOLD
	ld e,ZX_SPACE
	cp ' '
	jr z,kf_set
	ld e,ZX_EXTRA
	cp '-'
	jr z,kf_set
	ld e,ZX_ZERO			; other keys: as 0 (no song)
	and 0DFh			; lower case -> upper case
	sub 'A'
	jr c,kf_set
	cp 26
	jr nc,kf_set
	ld e,a
	ld d,0
	ld hl,zx_letters
	add hl,de
	ld e,(hl)
kf_set:
	ld a,e
	ld (key_down),a
	ld a,b
	ld (key_timer),a
	ret
kf_hold:
	ld hl,key_timer
	ld a,(hl)
	or a
	ret z
	dec (hl)
	ret nz
	ld a,0FFh
	ld (key_down),a
	ret

; ---- key_scan
; ROM KEY-SCAN (028Eh): E = code of the key that is down, FFh = none.
key_scan:
	ld a,(key_down)
	ld e,a
	ld d,0FFh			; no shift
	ret

; ---- song_extra
; End of song_for_key (C016h): '-' (ZX_EXTRA) chooses the 27th song, that
; no key chose on the Spectrum (A4A6h there). The noise mask is 1Fh as for
; L-Z. Other keys: frame_play as before (the return address of
; song_for_key is still on the stack, frame_play takes it).
song_extra:
	cp ZX_EXTRA
	jp nz,frame_play
	ld hl,song_nokey
	ret

; KEY-SCAN codes of the letters A-Z
zx_letters:
	defb 026h,000h,00Fh,016h,015h,00Eh,006h,001h,012h,009h,011h,019h,010h
	defb 008h,01Ah,022h,025h,00Dh,01Eh,005h,00Ah,007h,01Dh,017h,002h,01Fh

; =====================================================================
; Screen (CGA-1V, EGA mode)
; =====================================================================

; ---- cga_clear
; Clear the CPU page of the CGA (16000 bytes).
cga_clear:
	ld hl,CGA
	ld de,CGA+1
	ld bc,CGA_SIZE-1
	ld (hl),0
	ldir
	ret

; ---- cga_unpack
; cga_screen (RLE, see tools/make_tables.py) -> CGA page A.
cga_unpack:
	ld hl,cga_screen
	ld de,CGA
cu_loop:
	ld a,(hl)
	inc hl
	or a
	ret z
	cp 080h
	jr nc,cu_run
	ld c,a				; A literal bytes
	ld b,0
	ldir
	jr cu_loop
cu_run:
	sub 07Eh			; the next byte A - 7Eh times
	ld b,a
	ld a,(hl)
	inc hl
cu_r:
	ld (de),a
	inc de
	djnz cu_r
	jr cu_loop

; ---- pal_init
; Palette entry band * 32 + code * 2 + pixel: pixel 0 black, pixel 1 the
; colour of the code (rgb_table), for the 7 bands of 32 lines.
pal_init:
	xor a
	ld (CGA_PAL_ADDR),a
	ld c,7
pi_band:
	ld hl,rgb_table
	ld b,16
pi_code:
	xor a
	ld (CGA_PAL_DATA),a
	ld (CGA_PAL_DATA),a
	ld (CGA_PAL_DATA),a
	ld a,(hl)
	inc hl
	ld (CGA_PAL_DATA),a
	ld a,(hl)
	inc hl
	ld (CGA_PAL_DATA),a
	ld a,(hl)
	inc hl
	ld (CGA_PAL_DATA),a
	djnz pi_code
	dec c
	jr nz,pi_band
	ret

; ---- pal_rgb
; Palette entry A = R, G, B at HL. Keeps all registers.
pal_rgb:
	ld (CGA_PAL_ADDR),a
	push af
	ld a,(hl)
	ld (CGA_PAL_DATA),a
	inc hl
	ld a,(hl)
	ld (CGA_PAL_DATA),a
	inc hl
	ld a,(hl)
	ld (CGA_PAL_DATA),a
	dec hl
	dec hl
	pop af
	ret

; ---- anim_colour
; A = Spectrum attribute of the line animation (the original filled the
; attributes of rows 0-15 with it): its colour code (BRIGHT * 8 + INK) for
; ANIM_CODE in the bands of the animation. Written to the palette in the
; next vertical blank (pal_flush). Keeps BC, DE, HL.
anim_colour:
	and 047h
	bit 6,a
	jr z,acl_n
	xor 048h
acl_n:
	ld (pal_anim),a
	push hl
	ld hl,pal_dirty
	set 0,(hl)
	pop hl
	ret

; ---- anim_clear
; Clear the line animation (Spectrum lines 0-127 = CGA lines 4-131, code
; ANIM_CODE) and draw its frame again: lines 0 and 127, x = 0 and 255.
anim_clear:
	if DIAG				; build.cmd diag: no drawing (snow test)
	ret
	endif
	ld hl,anim_lines
	ld b,128
acr_line:
	ld e,(hl)
	inc hl
	ld d,(hl)
	inc hl
	push hl
	push bc
	ld a,b				; first and last line: full
	cp 128
	jr z,acr_full
	dec a
	jr z,acr_full
	ex de,hl			; x = 0, inside, x = 255
	ld (hl),088h
	inc hl
	ld b,62
acr_in:
	ld (hl),ANIM_CODE
	inc hl
	djnz acr_in
	ld (hl),018h
	jr acr_next
acr_full:
	ex de,hl
	ld b,64
acr_f:
	ld (hl),0F8h
	inc hl
	djnz acr_f
acr_next:
	pop bc
	pop hl
	djnz acr_line
	ret

; ---- plot_xor (ROM PLOT-SUB with OVER 1)
; B = y (48-175 from the bottom, the animation), C = x: invert the pixel
; on the CGA, COORDS = BC. Changes AF, DE, HL (not BC: draw_xor keeps its
; loop in the other register set and steps from COORDS).
plot_xor:
	ld (coords),bc
	if DIAG				; build.cmd diag: no drawing (snow test)
	ret
	endif
	ld a,175			; Spectrum line 175 - y = 0-127
	sub b
	ld l,a
	ld h,0
	add hl,hl
	ld de,anim_lines
	add hl,de
	ld e,(hl)
	inc hl
	ld d,(hl)
	ld a,c				; + x / 4
	rrca
	rrca
	and 03Fh
	ld l,a
	ld h,0
	add hl,de
	ld a,c				; pixel bit 7 - (x & 3)
	and 003h
	ld e,a
	ld d,0
	ex de,hl
	push bc
	ld bc,px_mask
	add hl,bc
	pop bc
	ld a,(hl)
	ex de,hl
	xor (hl)
	ld (hl),a
	ret

px_mask:
	defb 080h,040h,020h,010h

; ---- draw_xor (ROM DRAW-LINE)
; B = |dy|, C = |dx|, D = sign of dy, E = sign of dx (+1 / -1): line from
; COORDS like the ROM does it: the longer side steps every time, the
; shorter one when the sum of its length passes the longer one (from
; half). The loop state is in the other register set while plot_xor runs.
draw_xor:
	ld a,c
	cp b
	jr nc,dx_xge
	ld l,c				; |dy| > |dx|: L = shorter
	push de				; diagonal step
	xor a
	ld e,a				; straight step: dy only
	jr dx_larger
dx_xge:
	or c
	ret z
	ld l,b
	ld b,c
	push de
	ld d,0				; straight step: dx only
dx_larger:
	ld h,b				; H = longer, B = steps
	ld a,b
	rra
dx_loop:
	add a,l
	jr c,dx_diag
	cp h
	jr c,dx_straight
dx_diag:
	sub h
	ld c,a
	exx
	pop bc
	push bc
	jr dx_step
dx_straight:
	ld c,a
	push de
	exx
	pop bc
dx_step:
	ld hl,(coords)			; L = x, H = y
	ld a,b
	add a,h
	ld b,a
	ld a,c
	add a,l
	ld c,a
	call plot_xor
	exx
	ld a,c
	djnz dx_loop
	pop de
	ret

; ---- vu_cga
; VU meters (vu_meters of the original, FEC4h): a bar for each channel
; with a tone, as high as its volume (0-15 rows of vu_cga_rows), of the
; byte 7Eh (CGA: 77h, E7h). Only the rows between the old and the new
; height change.
vu_cga:
	if DIAG				; build.cmd diag: no drawing (snow test)
	ret
	endif
	ld b,3				; channel 3, 2, 1
vc_chan:
	push bc
	ld hl,vu_base			; tone period of the channel (as FEDAh)
	ld de,0014h
vc_add:
	add hl,de
	djnz vc_add
	ld a,(hl)
	inc hl
	or (hl)
	inc hl
	jr z,vc_h			; no tone: height 0
	ld a,(hl)			; volume
	and 00Fh
vc_h:
	ld c,a				; C = new height
	pop af
	push af
	dec a
	ld e,a				; DE = channel - 1
	ld d,0
	ld hl,vu_height
	add hl,de
	ld b,(hl)			; B = old height
	ld (hl),c
	add a,a				; CGA offset (channel - 1) * 4
	add a,a
	ld e,a
	ld a,c
	cp b
	jr z,vc_next
	jr c,vc_lower
vc_up:					; rows B .. C - 1: bar
	ld a,b
	call vu_row
	ld (hl),077h
	inc hl
	ld (hl),0E7h
	inc b
	ld a,b
	cp c
	jr nz,vc_up
	jr vc_next
vc_lower:				; rows C .. B - 1: clear
	dec b
	ld a,b
	call vu_row
	ld (hl),007h
	inc hl
	ld (hl),007h
	ld a,b
	cp c
	jr nz,vc_lower
vc_next:
	pop bc
	djnz vc_chan
	ret

; HL = vu_cga_rows[A] + DE. Keeps BC, DE.
vu_row:
	add a,a
	ld l,a
	ld h,0
	push de
	ld de,vu_cga_rows
	add hl,de
	ld a,(hl)
	inc hl
	ld h,(hl)
	ld l,a
	pop de
	add hl,de
	ret

; ---- scroll_cga
; Scroller (scroller of the original, FF28h): the text moves 2 pixels a
; frame through columns 1-30 of row 23, a new character every 4 frames.
; The characters get the colour codes 9-15 in turn and every frame the
; colours of these codes move one code on in the palette (scr_rainbow):
; the rainbow runs to the left one character a frame, faster than the
; text (the original shifted the colours one column a frame).
;
; Two strips hold the text as CGA bytes (4 pixels + colour code): strip
; A byte j = pixels 4j to 4j+3 of the text, strip B byte j = pixels 4j+2
; to 4j+5. A frame copies 60 bytes of each of the 8 lines from strip A
; (even frames) or B (odd frames) to the CGA. A strip line is a ring of
; 64 bytes stored twice (j and j + 64), so 60 bytes from any j are in a
; row. scr_frame counts the frames: j = frame / 2 mod 64; character n is
; drawn into bytes 2n - 1 to 2n + 1 at frame 4n - 120, before it shows.
scroll_cga:
	if DIAG				; build.cmd diag: no drawing (snow test)
	ret
	endif
	ld a,(scr_frame)
	and 3
	call z,scr_char
	ld a,(scr_frame)
	ld hl,STRIP_A
	rrca				; CY = odd frame: strip B
	jr nc,sc_a
	ld hl,STRIP_B
sc_a:
	and 03Fh			; j = frame / 2 mod 64
	ld e,a
	ld d,0
	add hl,de
	ld de,SCROLL_CGA
	ld a,8
sc_line:
	push hl
	push de
	rept 60
	ldi
	endm
	pop hl				; next CGA line
	ld bc,80
	add hl,bc
	ex de,hl
	pop hl				; next strip line
	ld bc,128
	add hl,bc
	dec a
	jp nz,sc_line
	ld hl,scr_frame
	inc (hl)
; ---- scr_rainbow
; Codes 9-15 in bands 5 and 6 (CGA lines 160-199, only the scroller uses
; them there): code 9 + k gets bright colour 1 + (k + scr_rot) mod 7, in
; the next vertical blank (pal_flush).
scr_rainbow:
	ld a,(scr_rot)
	inc a
	cp 7
	jr c,sr_rot
	xor a
sr_rot:
	ld (scr_rot),a
	ld hl,pal_dirty
	set 1,(hl)
	ret

; ---- pal_flush
; Palette changes, from the interrupt in the vertical blank of the CGA-1V
; (a RAMDAC written while it draws disturbs the picture: "snow"). Bit 0
; of pal_dirty: colour of the animation (pal_anim), bit 1: rainbow of the
; scroller (scr_rot). Keeps all but AF.
pal_flush:
	push bc
	push de
	push hl
	ld a,(pal_dirty)
	ld c,a
	xor a
	ld (pal_dirty),a
	bit 0,c
	jr z,pf_rainbow
	ld a,(pal_anim)			; HL = rgb_table + 3 * code
	ld l,a
	add a,a
	add a,l
	ld e,a
	ld d,0
	ld hl,rgb_table
	add hl,de
	ld a,ANIM_CODE*2+1		; bands 0-4
	ld b,5
pf_band:
	call pal_rgb
	add a,32
	djnz pf_band
pf_rainbow:
	bit 1,c
	jr z,pf_end
	ld a,(scr_rot)
	ld c,a				; C = (k + rot) mod 7 for k = 0
	ld b,0				; B = k
pf_code:
	ld a,c				; HL = rgb_table + 3 * (9 + C)
	add a,9
	ld l,a
	add a,a
	add a,l
	ld e,a
	ld d,0
	ld hl,rgb_table
	add hl,de
	ld a,b				; entry 5 * 32 + (9 + k) * 2 + 1
	add a,a
	add a,5*32+9*2+1
	call pal_rgb
	add a,32			; band 6
	call pal_rgb
	inc c
	ld a,c
	cp 7
	jr c,pf_c
	ld c,0
pf_c:
	inc b
	ld a,b
	cp 7
	jr nz,pf_code
pf_end:
	pop hl
	pop de
	pop bc
	ret

; ---- scr_char
; The next character of the text into the strips at j = frame / 2 + 60.
scr_char:
	ld hl,(text_ptr)		; text, FFh = back to the start
sch_ch:
	ld a,(hl)
	cp 0FFh
	jr nz,sch_ok
	ld hl,(text_start)
	jr sch_ch
sch_ok:
	inc hl
	ld (text_ptr),hl
	sub 020h			; IX = glyph (font: characters 20h-7Fh)
	ld l,a
	ld h,0
	add hl,hl
	add hl,hl
	add hl,hl
	ld de,font
	add hl,de
	push hl
	pop ix
	ld a,(scr_code)			; next colour: codes 9-15
	inc a
	cp 16
	jr c,sch_c
	ld a,9
sch_c:
	ld (scr_code),a
	ld (sch_code),a
	ld a,(scr_frame)		; C = j
	rrca
	add a,60
	and 03Fh
	ld c,a
	ld hl,STRIP_A
	ld b,8
sch_line:
	push bc
	push hl
	ld a,(sch_code)
	ld e,a				; E = code
	ld d,(ix+0)			; D = glyph line
	ld a,d				; A[j] = pixels 0-3
	and 0F0h
	or e
	call ring_put
	inc c
	ld a,d				; A[j + 1] = pixels 4-7
	add a,a
	add a,a
	add a,a
	add a,a
	or e
	call ring_put
	ld de,STRIP_B-STRIP_A		; strip B
	add hl,de
	ld a,(sch_code)
	ld e,a
	ld d,(ix+0)
	dec c
	dec c				; B[j - 1] |= pixels 0-1 (low half)
	ld a,d
	rrca
	rrca
	and 030h
	call ring_or
	inc c				; B[j] = pixels 2-5
	ld a,d
	add a,a
	add a,a
	and 0F0h
	or e
	call ring_put
	inc c				; B[j + 1] = pixels 6-7 (high half)
	ld a,d
	rrca
	rrca
	and 0C0h
	or e
	call ring_put
	inc ix
	pop hl
	ld de,128
	add hl,de
	pop bc
	djnz sch_line
	ret

sch_code:	defb 0

; ---- ring_put, ring_or
; Strip line HL (a multiple of 128), byte C (mod 64) = A / |= A, in both
; copies (C and C + 64). Keeps BC, DE, HL.
ring_put:
	push hl
	push af
	ld a,c
	and 03Fh
	or l
	ld l,a
	pop af
	ld (hl),a
	set 6,l
	ld (hl),a
	pop hl
	ret
ring_or:
	push hl
	push af
	ld a,c
	and 03Fh
	or l
	ld l,a
	pop af
	or (hl)
	ld (hl),a
	set 6,l
	ld (hl),a
	pop hl
	ret

; ---- scr_init
; Empty strips.
scr_init:
	ld hl,STRIP_A
	ld de,STRIP_A+1
	ld bc,2*8*128-1
	ld (hl),0
	ldir
	ret

; =====================================================================
; Sound: AY-3-8912 registers -> YM3812
; =====================================================================

; The player writes the AY registers R0-R10 in each tick (ay_regs). The
; YM3812 plays them: channels 0-2 the tones of AY channels A-C, channel 3
; the noise. Tone: period P (12 bits), 1.7734 MHz / 16 / P = 110837.5 / P
; Hz, the same constant as the MZ-800 PSG of the Flappy port (110840):
; F-number = K / (P << block), K = 110840 * 2^20 / 49716 = 23ABECh
; (fnum_table, tools/make_tables.py).
; Noise: one generator (period R6) for all channels; the YM3812 channel
; gets the loudest volume of the channels with noise on. A channel with
; both tone and noise (the AY outputs tone AND noise) plays its tone 6 dB
; lower. AY volume 0-15 -> TL in steps of 3 dB, 0 = key off.

ym_init:
	ld hl,ym_regs
yi_loop:
	ld a,(hl)			; register, value pairs, FFh ends
	inc a
	ret z
	dec a
	inc hl
	ld e,(hl)
	inc hl
	call ym_write
	jr yi_loop

; tone channels 0-2: modulator with feedback (buzzy, like a square),
; carrier sustained; channel 3: noisy modulator (multiple 15, feedback 7)
ym_regs:
	defb 001h,020h			; WSE
	defb 008h,000h
	defb 0BDh,000h
	defb 020h,021h, 021h,021h, 022h,021h, 023h,021h, 024h,021h, 025h,021h
	defb 040h,01Ch, 041h,01Ch, 042h,01Ch, 043h,03Fh, 044h,03Fh, 045h,03Fh
	defb 060h,0F0h, 061h,0F0h, 062h,0F0h, 063h,0F0h, 064h,0F0h, 065h,0F0h
	defb 080h,00Fh, 081h,00Fh, 082h,00Fh, 083h,00Fh, 084h,00Fh, 085h,00Fh
	defb 0E0h,000h, 0E1h,000h, 0E2h,000h, 0E3h,000h, 0E4h,000h, 0E5h,000h
	defb 0C0h,00Ch, 0C1h,00Ch, 0C2h,00Ch
	defb 028h,02Fh, 02Bh,021h	; channel 3 (slots 8 and 11)
	defb 048h,000h, 04Bh,03Fh
	defb 068h,0F0h, 06Bh,0F0h
	defb 088h,00Fh, 08Bh,00Fh
	defb 0E8h,000h, 0EBh,000h
	defb 0C3h,00Eh
	defb 0B0h,000h, 0B1h,000h, 0B2h,000h, 0B3h,000h
	defb 0FFh

; ---- ym_silence
ym_silence:
	ld a,0B0h
ys_loop:
	ld e,0
	push af
	call ym_write
	pop af
	inc a
	cp 0B4h
	jr nz,ys_loop
	ret

; ---- ym_write
; YM3812 register A = E. The chip needs 12 of its clocks after the
; address and 84 after the data (3.3 us and 23.5 us, 94 T at 4 MHz).
; Keeps BC, DE, HL.
ym_write:
	out (YMADDR),a
	ex (sp),hl
	ex (sp),hl
	ld a,e
	out (YMDATA),a
	push bc
	ld b,7
yw_wait:
	djnz yw_wait
	pop bc
	ret

; ---- opl_update
; The AY registers in ay_regs -> YM3812 (only what changed is written).
opl_update:
	ld hl,ay_regs			; R0-R10 as last time: nothing to do
	ld de,ou_last
	ld b,11
ou_cmp:
	ld a,(de)
	cp (hl)
	jr nz,ou_changed
	inc hl
	inc de
	djnz ou_cmp
	ret
ou_changed:
	ld hl,ay_regs
	ld de,ou_last
	ld bc,11
	ldir
	xor a
	ld (ou_noise_vol),a
	ld c,0				; channel 0-2
ou_chan:
	ld a,(ay_reg7)			; tone on: bit C = 0
	ld b,c
	inc b
ou_bit:
	rrca
	djnz ou_bit			; CY = tone off
	sbc a,a
	cpl
	ld (ou_tone),a			; FFh = tone on
	ld a,(ay_reg7)			; noise on: bit C + 3 = 0
	rrca
	rrca
	rrca
	ld b,c
	inc b
ou_nbit:
	rrca
	djnz ou_nbit
	sbc a,a
	cpl
	ld (ou_nz),a			; FFh = noise on
	ld hl,ay_regs+8			; volume
	ld e,c
	ld d,0
	add hl,de
	ld a,(hl)
	and 00Fh
	ld b,a				; B = volume
	ld a,(ou_nz)
	or a
	jr z,ou_tvol
	ld a,(ou_noise_vol)		; the loudest channel with noise
	cp b
	jr nc,ou_nmax
	ld a,b
	ld (ou_noise_vol),a
ou_nmax:
	ld a,(ou_tone)			; tone and noise: tone 6 dB lower
	or a
	jr z,ou_tvol
	ld a,b
	sub 2
	jr nc,ou_t2
	xor a
ou_t2:
	ld b,a
ou_tvol:
	ld a,(ou_tone)
	and b
	ld b,a				; B = volume of the tone (0 = off)
	ld hl,ay_regs			; DE = period
	add hl,de
	add hl,de
	ld e,(hl)
	inc hl
	ld a,(hl)
	and 00Fh
	ld d,a
	push bc
	ld a,c
	call ym_voice
	pop bc
	inc c
	ld a,c
	cp 3
	jr nz,ou_chan
	ld a,(ay_reg6)			; noise: period 0-31 (0 = 1)
	and 01Fh
	jr nz,ou_np
	inc a
ou_np:
	ld e,a
	ld d,0
	ld a,(ou_noise_vol)
	ld b,a
	ld a,3
	jp ym_voice

ou_last:	defb 0,0,0,0,0,0,0,0FFh,0,0,0	; R0-R10 of the last update
ou_tone:	defb 0
ou_nz:		defb 0
ou_noise_vol:	defb 0

; ---- ym_voice
; YM3812 channel A (0-3): AY period DE, AY volume B (0-15, 0 = off).
ym_voice:
	ld c,a
	ld l,a				; IX = ym_state + 8 * channel
	ld h,0
	add hl,hl
	add hl,hl
	add hl,hl
	push de
	ld de,ym_state
	add hl,de
	pop de
	push hl
	pop ix
	ld a,d				; period 0 sounds as 1 on the AY
	or e
	jr nz,yv_p
	inc e
yv_p:
	ld a,(ix+0)			; a new period: F-number, block
	cp e
	jr nz,yv_new
	ld a,(ix+1)
	cp d
	jr z,yv_vol
yv_new:
	ld (ix+0),e
	ld (ix+1),d
	push bc
	call ym_fnum			; HL = F-number, B = block, CY = too high
	ld a,0
	jr nc,yv_ok
	ld a,c				; too high: tones are silent, the noise
	cp 3				; plays at the top of the YM3812
	ld a,1
	jr nz,yv_ok
	ld hl,1023
	ld b,7
	xor a
yv_ok:
	ld (ix+5),a			; 1 = silent
	ld a,b
	add a,a
	add a,a
	or h
	ld (ix+3),a			; block, F-number high
	ld (ix+2),l
	pop bc
	ld e,l				; F-number low
	ld a,c
	add a,0A0h
	call ym_write
yv_vol:
	ld a,b				; volume -> TL of the carrier
	cp (ix+6)
	jr z,yv_key
	ld (ix+6),a
	ld hl,ym_tl
	ld e,a
	ld d,0
	add hl,de
	ld e,(hl)
	ld hl,ym_car
	ld d,0
	push bc
	ld b,0
	add hl,bc
	pop bc
	ld a,(hl)
	call ym_write
yv_key:
	ld a,(ix+3)			; KEY ON when it sounds
	ld e,a
	ld a,b
	or a
	jr z,yv_off
	ld a,(ix+5)
	or a
	jr nz,yv_off
	set 5,e
yv_off:
	ld a,e
	cp (ix+4)
	ret z
	ld (ix+4),a
	ld a,c
	add a,0B0h
	jp ym_write

; ---- ym_fnum
; DE = period 1-4095 -> HL = F-number, B = block, CY = 1 when the tone is
; above the YM3812 (period < 18, over 6 kHz). The period is shifted left
; (block) until it is over K >> 10, then fnum_table has K / period.
; Keeps C.
ym_fnum:
	ld b,0
yf_blk:
	ld hl,FNUM_LO-1
	or a
	sbc hl,de
	jr c,yf_tab			; P << block >= FNUM_LO
	ld a,b
	cp 7
	jr z,yf_max
	inc b
	ex de,hl
	add hl,hl
	ex de,hl
	jr yf_blk
yf_max:
	ld hl,1023
	scf
	ret
yf_tab:
	ex de,hl			; HL = fnum_table[(P - FNUM_LO) / 4]
	ld de,-FNUM_LO
	add hl,de
	srl h
	rr l
	srl h
	rr l
	add hl,hl
	ld de,fnum_table
	add hl,de
	ld a,(hl)
	inc hl
	ld h,(hl)
	ld l,a
	or a
	ret

; AY volume 0-15 -> total level of the carrier (0.75 dB): 3 dB a step
ym_tl:
	defb 63,56,52,48,44,40,36,32,28,24,20,16,12,8,4,0
ym_car:
	defb 043h,044h,045h,04Bh	; carrier slots of channels 0-3

; per channel: period (2), F-number low, B0h value without KEY ON, last
; B0h value, 1 = too high, volume, (spare)
ym_state:
	defb 0FFh,0FFh,0,0,0,0,0FFh,0
	defb 0FFh,0FFh,0,0,0,0,0FFh,0
	defb 0FFh,0FFh,0,0,0,0,0FFh,0
	defb 0FFh,0FFh,0,0,0,0,0FFh,0

; =====================================================================
; Variables
; =====================================================================

isr_sp:		defw 0			; SP of the interrupted code
isr_stack:	defs 32			; stack of the quick part of isr
isr_stack_top:
frames:		defb 0			; FRAMES (5C78h): counted each frame
frame_div:	defb FRAME_TICKS	; interrupts to the next frame
frame_busy:	defb 0			; 1 = the work of a frame runs
frames_lost:	defb 0			; frames that came while the last one ran
ticks_owed:	defb 0			; their player ticks, not played yet
music_on:	defb 0			; 1 = IM 2 of the original (isr_body runs)
kbd_state:	defb 0			; 1 = STROBE taken, ACK on
kbd_code:	defb 0			; key from the interrupt (0 = none)
key_down:	defb 0FFh		; KEY-SCAN code of the key that is down
key_timer:	defb 0			; frames it stays down
song_mark:	defb 0			; written by the 8Ch calls of song Y
coords:		defw 0			; COORDS (5C7Dh): x, y of the last point
scr_frame:	defb 0			; scroller: frames
scr_code:	defb 8			; scroller: colour code of the last character
scr_rot:	defb 0			; scroller: rotation of the rainbow (0-6)
pal_anim:	defb 7			; colour code of the animation (pal_flush)
pal_dirty:	defb 0			; palette to write: bit 0 animation, bit 1 rainbow
page0_save:	defs 3
vu_height:	defb 0,0,0		; bars on the screen (channels A, B, C)

; The first bytes of the Spectrum ROM: a channel without a pitch effect
; (command 86h) reads them as one (init_song sets 0000h on the Spectrum).
; Songs E, F and R read 0000h-0026h (tools/player.py, ROM_HEAD).
rom_head:
	defb 0F3h,0AFh,011h,0FFh,0FFh,0C3h,0CBh,011h,02Ah,05Dh,05Ch,022h,05Fh,05Ch,018h,043h
	defb 0C3h,0F2h,015h,0FFh,0FFh,0FFh,0FFh,0FFh,02Ah,05Dh,05Ch,07Eh,0CDh,07Dh,000h,0D0h
	defb 0CDh,074h,000h,018h,0F7h,0FFh,0FFh,0FFh,0C3h,05Bh,033h,0FFh,0FFh,0FFh,0FFh,0FFh
	defb 0C5h,02Ah,061h,05Ch,0E5h,0C3h,09Eh,016h,0F5h,0E5h,02Ah,078h,05Ch,023h,022h,078h
