"""Annotations for tools/mkdis.py (Fuxoft Soundtrack IV disassembly)."""

# (start, end_exclusive, name)
SEGMENTS = [
    (0x744A, 0x10000, 'CODE block'),
]

ENTRIES = [
    0x8462,     # BASIC 20, 9215: RANDOMIZE USR 33890 (line animation, returns on a key)
    0x84EC,     # after 'jp z,exit_basic' when BASIC 9200 pokes CAh to 84E9h (34025)
    0xC15C,     # BASIC 9600: RANDOMIZE USR 49500 (start song A and the interrupt)
    0xC353,     # BASIC 9999: LET l=USR 50003 (stop the music)
    0xC356,     # jump vector: one player tick (not used by the program)
    0xC3C4,     # IM 2 handler (jp at FFF4h, set up at C3A8h)
    0x86AA, 0x86AE,   # machine code called from song data (command 8Ch)
] + [0xC770, 0xC77C, 0xC78A, 0xC794, 0xC7A6, 0xC7B1, 0xC7DE, 0xC7BC,     # command handlers 80h-8Eh
     0xC7CC, 0xC7D7, 0xC7EE, 0xC7FC, 0xC80A, 0xC817, 0xC827]             # (dispatched by push/ret)

# song headers (key, address), from the key table at C016h (KEY-SCAN codes)
SONGS = [
    ('A', 0xC83C), ('B', 0xD179), ('C', 0xD4DA), ('D', 0xD7B4), ('E', 0xD9D5), ('F', 0xDEB2),
    ('G', 0xE14B), ('H', 0xE894), ('I', 0xEC31), ('J', 0xEE8E), ('K', 0xF23A), ('L', 0xF9B0),
    ('M', 0xBCFC), ('N', 0xBA54), ('O', 0xB748), ('P', 0xB234), ('Q', 0xADE8), ('R', 0xAA50),
    ('S', 0xA64A), ('T', 0x9CE0), ('U', 0x98F8), ('V', 0x940C), ('W', 0x8B83), ('X', 0x89E4),
    ('Y', 0x85D4), ('Z', 0x8E2B),
    ('-', 0xA4A6),      # a 27th song: no key selects it
]

# song data areas (only these are walked for unreached '80 w' jumps)
SONG_RANGES = [(0x85D4, 0xC000), (0xC83C, 0xFEC4)]

# calls that never return / instructions after which code does not continue
NORETURN = set()
NORETURN_AFTER = set()

# bytes that are never code in the image (FFF4h jp isr and FFFFh jr are written by init_song)
DATA_FORCE = {0xFFF4, 0xFFF5, 0xFFF6, 0xFFFF}

# (start, end_exclusive, kind) kind = 'db' | 'dw' | 'dwn' (words that are numbers) | 'text' | 'font'
DATA_RANGES = [
    (0x744A, 0x815F, 'text'),     # scroll text
    (0x8160, 0x8460, 'font'),     # characters 20h-7Fh (CHARS = 8060h, BASIC 9020)
    (0xC200, 0xC302, 'db'),       # IM 2 vector table, all FFh -> FFFFh
    (0xC49C, 0xC544, 'dwn'),      # AY tone periods of notes 1-84 (numbers)
    (0xC752, 0xC770, 'dw'),       # command handlers 80h-8Eh
    (0xC835, 0xC83B, 'dw'),       # header of the current song
    (0xFF06, 0xFF28, 'dw'),       # VU meter rows, scroll text start and pointer
]

# immediates in these ranges are taken as addresses
IMM_RANGES = [(0x744A, 0x10000)]
IMM_NUM = {
    0xC58B,     # ld bc,0FFFDh: AY register select port
    0x85AE,     # ld hl,2FC4h: ROM bytes used as random numbers
    0x85B6,     # ld hl,2FFEh
    0x85BC,     # ld de,0562h
    0x852E,     # ld hl,0101h: DRAW signs
    0xC393,     # ld hl,0000h: clear channel flags, transpose and pitch effect
    0xC6F0,     # ld de,0000h: rest = tone period 0
}
IMM_ADDR = set()

# addresses outside the image with a name (Spectrum ROM, screen, system variables)
EQU = {
    0x0000: 'rom_start',      # written by the 8Ch stubs (no effect on the Spectrum)
    0x0038: 'rom_mask_int',
    0x028E: 'rom_key_scan',
    0x22E5: 'rom_plot_sub',
    0x24BA: 'rom_draw_line',
    0x2758: 'basic_hl_alt',   # HL' expected by BASIC after USR
    0x5800: 'attrs',
    0x5AE0: 'attr_row23',
    0x5AE1: 'attr_row23_1',
    0x5AE2: 'attr_row23_2',
    0x5AFE: 'attr_row23_30',
    0x5AFF: 'attr_row23_31',
    0x57FF: 'scr_r23_c31_l7', # character row 23, column 31, pixel line 7
    0x50FF: 'scr_r23_c31',    # pixel line 0
    0x5B00: 'line_buf',       # printer buffer: line end points
    0x5C36: 'sv_chars',
    0x5C3A: 'sv_err_nr',      # IY base for BASIC
    0x5C78: 'sv_frames',
}

NAMES = {
    # scroll text and font
    0x744A: 'scroll_text', 0x815F: 'scroll_text_end', 0x8160: 'font',
    # line animation (BASIC USR 33890)
    0x8462: 'lines', 0x8487: 'lines_new_dir', 0x849B: 'lines_loop', 0x84C2: 'lines_colour_ptr',
    0x84E9: 'lines_exit_jp', 0x84EC: 'lines_after_key', 0x84FA: 'fill_page',
    0x8500: 'colours', 0x8501: 'colours_1',
    0x8512: 'draw_line', 0x8544: 'move_y', 0x8564: 'move_x', 0x8580: 'move_store', 0x858C: 'bounce',
    0x8593: 'lines_key', 0x859B: 'exit_basic',
    0x85A4: 'lines_new', 0x85A5: 'lines_ptr', 0x85A7: 'lines_delta',
    0x85AB: 'random', 0x85AF: 'random_rom', 0x85BD: 'random_seq',
    0x86AA: 'song_mark2', 0x86AE: 'song_mark1',
    # interrupt, keys and player
    0xC000: 'frame', 0xC004: 'select_song', 0xC016: 'song_for_key', 0xC0F8: 'frame_play',
    0xC15C: 'start_music', 0xC161: 'set_noise_mask', 0xC165: 'noise_mask_val',
    0xC170: 'restore_im1', 0xC180: 'isr_body', 0xC200: 'im2_table',
    0xC350: 'jp_init', 0xC353: 'jp_stop', 0xC356: 'jp_tick',
    0xC359: 'init_song', 0xC3C4: 'isr', 0xC3D7: 'stop_music',
    0xC3E6: 'ay_regs', 0xC3EC: 'ay_reg6', 0xC3ED: 'ay_reg7', 0xC3F3: 'ay_reg13',
    0xC3F4: 'noise', 0xC3F5: 'channel', 0xC3F6: 'save_sp', 0xC3F8: 'save_hl',
    0xC3FA: 'sp_a', 0xC3FC: 'sp_b', 0xC3FE: 'sp_c',
    0xC400: 'stack_a', 0xC420: 'stack_b', 0xC440: 'stack_c',
    0xC453: 'vu_base', 0xC460: 'chan_a', 0xC474: 'chan_b', 0xC488: 'chan_c',
    0xC49C: 'tone_table',
    0xC544: 'tick', 0xC585: 'ay_write', 0xC58A: 'ay_write_loop', 0xC59B: 'set_reg',
    0xC5A4: 'chan_end', 0xC5B0: 'chan_tick', 0xC5BE: 'env_tick', 0xC5C3: 'env_read',
    0xC5F9: 'fx_tick', 0xC60F: 'fx_read', 0xC682: 'chan_out', 0xC6B8: 'store_ptr',
    0xC6BF: 'note_read', 0xC6F0: 'note_rest', 0xC6F3: 'note_len', 0xC723: 'env_start',
    0xC73C: 'note_cmd', 0xC752: 'cmd_table',
    0xC770: 'cmd_jump', 0xC77C: 'cmd_call', 0xC78A: 'cmd_loop', 0xC794: 'cmd_endloop',
    0xC7A6: 'cmd_noise', 0xC7B1: 'cmd_mixer', 0xC7BC: 'cmd_env', 0xC7CC: 'cmd_transp',
    0xC7D7: 'cmd_ret', 0xC7DE: 'cmd_fx', 0xC7EE: 'cmd_env_once', 0xC7FC: 'cmd_env_loop',
    0xC80A: 'cmd_code', 0xC817: 'cmd_noise_add', 0xC81C: 'noise_mask', 0xC827: 'cmd_transp_add',
    0xC835: 'song_hdr',
    # VU meters and scroller
    0xFEC4: 'vu_meters', 0xFF06: 'vu_rows', 0xFF24: 'text_start', 0xFF26: 'text_ptr',
    0xFF28: 'scroller', 0xFFF3: 'scroll_count', 0xFFF4: 'im2_jp', 0xFFF5: 'im2_jp_addr',
    0xFFFF: 'im2_jr',
}

COMMENTS = {
    0x744A: 'Scroll text (Czech, capital letters stand for letters with diacritics), FFh = end',
    0x8160: 'Font for characters 20h-7Fh, BASIC sets CHARS to 8060h',
    0x8460: 'Unused',
    0x8462: 'Line animation, called from BASIC in a loop (RANDOMIZE USR 33890).\n'
            'Draws bouncing lines with the ROM DRAW, end points in the printer buffer.\n'
            'Returns on a key (or on ENTER only, when BASIC pokes CAh to lines_exit_jp).',
    0x8500: 'Colours for the attribute cycle, 0 = back to the start (BASIC pokes colours_1)',
    0x85A4: 'Variables of the line animation',
    0x85AB: 'Random number: ROM bytes + R + FRAMES',
    0x85D4: 'Song data. Format: tools/player.py.',
    0x86AA: 'Called from song data (command 8Ch): writes to ROM, no effect on the Spectrum',
    0xC000: 'Interrupt work: a song key restarts that song, otherwise one player tick\n'
            '(3 ticks with ENTER held). The border is magenta during the tick.',
    0x9CBB: 'Never read by the player',
    0xC016: 'HL = song header for KEY-SCAN code A; noise mask 0Fh for A-K, 1Fh for L-Z',
    0xC113: 'Unused',
    0xC15C: 'USR 49500: start song A and the IM 2 interrupt, return to BASIC',
    0xC161: 'Set the noise mask of command 8Dh, then stop the music (IM 1, AY silent)',
    0xC180: 'Interrupt body: VU meters, scroller, keys and music',
    0xC200: 'IM 2 vector table (I = C2h): every vector is FFFFh -> jr -> FFF4h: jp isr',
    0xC350: 'Jump vectors',
    0xC359: 'Start the song in song_hdr and the IM 2 interrupt',
    0xC3D7: 'USR 50003: back to IM 1 and silence the AY',
    0xC3E6: 'Player variables, shadow of AY registers R0-R13',
    0xC400: 'Channel stacks (calls and loops of the note streams), 32 bytes each',
    0xC460: 'Channel blocks, 20 bytes each (layout in tools/player.py)',
    0xC49C: 'AY tone periods (1.7734 MHz clock), note 1 = A0',
    0xC544: 'One player tick (50 Hz): three channels, then all AY registers',
    0xC5B0: 'Tick of one channel. IX = channel block, HL = its stack, A = channel 1-3',
    0xC6BF: 'Next item of the note stream (note, rest or command)',
    0xC752: 'Note stream commands 80h-8Eh',
    0xC835: 'Header of the current song (copied from the song table)',
    0xC83C: 'Song data (continued)',
    0xFEC4: 'VU meters: bars of the channel volumes',
    0xFF28: 'Scroller in character row 23 (2 pixels per frame, a new character every 4 frames)',
    0xFF95: 'Unused (rests of a font), FFF3h-FFF6h and FFFFh are variables and the IM 2 jump',
}

LINE_CMT = {
    0x84E9: 'BASIC pokes C3h (jp) or CAh (jp z)',
    0xC164: 'operand set by song_for_key',
    0xC81B: 'operand set by set_noise_mask',
    0xC3D4: 'continue with the ROM interrupt (FRAMES, keyboard)',
}
