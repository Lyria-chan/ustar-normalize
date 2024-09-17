import os
metadata = []
sequence = []
multiplier = 0.5
notegap = 16 * multiplier # Best keep this a power of 2
careful_notegap = 8 * multiplier # 0 or False to disable, default 8
careful_notegap_multiplier = 7.95 # 7 by default
trim_note_length = 16 # 0 or False to disable
note_spacing = 2
aggressive_note_spacing = False # Enable if you know your song has a constant stream of notes
shortest_note_length = 1 # set if aggressive note spacing is enabled
normalize_notes = False
song_path = r'D:\Games\UltraStar Deluxe\songs' # Set this to the path of your song folder
filename = 'Eurobeat Brony ft. The Living Tombstone - Discord (Remix)' # Do NOT put in the .txt extension, just the name of the folder/txt file
language = 'English'
debug = False

even_breaks = True # False to disable first_note_timestamp
if even_breaks:
    careful_notegap = careful_notegap
first_note_offset = 0 # default 32 or 0
even_note_timestamp_start = -4 - first_note_offset
even_breaks_measure = 16 # default 64

class Note:
    def __init__(self, timestamp, length, pitch, lyric):
        self.timestamp = timestamp
        self.length = length
        self.pitch = pitch
        self.lyric = lyric
class Break:
    def __init__(self, timestamp):
        self.timestamp = timestamp

def scrape_song():
    global filename
    if filename == '':
        filename = input("Enter filename: ")
    global path
    path = os.path.join(song_path, filename, filename + ".txt")
    file = open(path, "r", encoding='utf-8')
    lines = file.readlines()
    # create a new backup file
    with open(os.path.join(song_path, filename, "backup.txt"), "w", encoding='utf-8') as backup:
        for line in lines:
            backup.write(line)
    for line in lines:
        indicator = line[0]
        match indicator:
            case "#":
                metadata.append(line)                
            case "-":
                #add a new break to the note sequence
                sequence.append(Break(int(line.split()[1])))
            case ":":
                a = line.split(" ", 4)
                note = Note(int(a[1]), int(a[2]), int(a[3]), a[4].replace("\n", ""))
                sequence.append(note)


def reconstruct_song(debug):
    global path
    if not debug:
        os.remove(path)
        file = open(path, "w", encoding='utf-8')
    else:
        file = open(os.path.join(song_path, filename, "debug.txt"), "w", encoding='utf-8')
    for line in metadata:
        file.write(line)
    for note in sequence:
        if isinstance(note, Break):
            file.write(f"- {note.timestamp}\n")
        else:
            file.write(f": {note.timestamp} {int(note.length)} {int(note.pitch)} {note.lyric}\n")
    file.write("E\n")

def trim_long_notes():
    if trim_note_length:
        for note in sequence:
            if isinstance(note, Note) and note.length > trim_note_length :
                note.length = trim_note_length

def trim_overlapping_notes():
    for note in sequence:
        if sequence.index(note) == len(sequence) - 1:
            break
        next_note = sequence[sequence.index(note) + 1]
        if isinstance(note, Note) and isinstance(next_note, Note):
            if note.timestamp + note.length >= next_note.timestamp:
                note.length = next_note.timestamp - note.timestamp - note_spacing
                if note.length <= 0:
                    if note_spacing > 1 and not aggressive_note_spacing:
                        note.length = 1
                    else:
                        if aggressive_note_spacing: note.length = shortest_note_length
                        else: note.length = 1
                        note.timestamp = next_note.timestamp - note.length - 1

def trim_notes_close_to_breaks():
    for note in sequence:
        if sequence.index(note) == len(sequence) - 1:
            break
        next_note = sequence[sequence.index(note) + 1]
        if isinstance(note, Note) and isinstance(next_note, Break):
            if multiplier > 1:
                note_cut_off = 2 - note_spacing
            else:
                note_cut_off = 1
            if next_note.timestamp - note.timestamp - note.length <= 4 * multiplier - note_cut_off:
                note.length = next_note.timestamp - note.timestamp - 4 * multiplier - note_cut_off
                if note.length <= 0: note.length = 1
                    
            
def add_breaks():
    global even_note_timestamp_start

    def sequence_insert_break(index, future_break):
        global even_note_timestamp_start
        print(f"Inserting break at index {index} with future_break timestamp {future_break.timestamp}")
        if not even_breaks:
            sequence.insert(index, future_break)
            print("Inserted without even breaks")
            return
        else:
            closest_break_timestamp = find_timestamp_of_closest_past_gap(future_break.timestamp)
            print(f"Closest break timestamp: {closest_break_timestamp}")
            while closest_break_timestamp > even_note_timestamp_start:
                even_note_timestamp_start += even_breaks_measure
                print(f"Updated even_note_timestamp_start: {even_note_timestamp_start}")
            if even_note_timestamp_start - 2 < future_break.timestamp:
                sequence.insert(index, future_break)
                even_note_timestamp_start += even_breaks_measure
                print(f"Inserted even break at: {future_break.timestamp}")
                
                

    for note in sequence:
        if sequence.index(note) == len(sequence) - 1:
            break
        
        next_note = sequence[sequence.index(note) + 1]
        potential_break = Break(next_note.timestamp - 2)

        if isinstance(note, Note) and isinstance(next_note, Note):
            if next_note.timestamp - note.timestamp >= notegap:
                sequence_insert_break(sequence.index(next_note), potential_break) 
            elif careful_notegap:
                if next_note.timestamp - note.timestamp >= careful_notegap:
                    closest_timestamp = find_timestamp_of_closest_past_gap(potential_break.timestamp)

                    if potential_break.timestamp - closest_timestamp - note.length >= careful_notegap * careful_notegap_multiplier:
                        sequence_insert_break(sequence.index(next_note), potential_break)
        
def find_timestamp_of_closest_past_gap(timestamp):
    closest_timestamp = 0
    for note in sequence[::-1]:
        if isinstance(note, Break):
            if note.timestamp < timestamp:
                closest_timestamp = note.timestamp
                return closest_timestamp
    return closest_timestamp

def additional_function(mode):
    global sequence
    def function_delete_breaks():
        for note in sequence:
            if isinstance(note, Break):
                sequence.remove(note)
    

    match mode:
        case 'delete_breaks':
            function_delete_breaks()
        
def merge_letter_polish_lyrics(letter):
    global sequence
    shorter_sequence = sequence[:-16]
    for index, note in enumerate(shorter_sequence):
        next_note = sequence[index+1]
        next_next_note = sequence[index + 2]
        if isinstance(note, Note) and isinstance(next_note, Note):
            if note.lyric.strip() == letter:
                roll_lyrics_left(index)
        elif (isinstance(note, Note) and isinstance(next_note, Break) and isinstance(next_next_note, Note)):
            if note.lyric.strip() == letter:
                roll_lyrics_left(index)
            
def roll_lyrics_left(starting_index):
    # idk why this is necessary but it is help me
    note = sequence[starting_index]
    next_note = sequence[starting_index + 1]
    if isinstance(next_note, Break):
        next_note = sequence[starting_index + 2]
    note.lyric = note.lyric + next_note.lyric

    for note in sequence[starting_index+1:]:
        if sequence.index(note) == len(sequence) - 1:
            break
        next_note = sequence[sequence.index(note) + 1]
        if isinstance(note, Note) and isinstance(next_note, Note):
            note.lyric = next_note.lyric
        # if there are more than two notes left in the sequence:
        elif sequence.index(note) < len(sequence) - 2:
            next_next_note = sequence[sequence.index(note) + 2]
            if isinstance(note, Note) and isinstance(next_note, Break) and isinstance(next_next_note, Note):
                note.lyric = next_next_note.lyric


def roll_lyrics_right(starting_index):
    note = sequence[starting_index]
    buffer = note.lyric
    note.lyric = '~'
    for note in sequence[starting_index+1:]:
        if isinstance(note, Note):
            buffer, note.lyric = note.lyric, buffer

def fix_capitalized_syllables():
    for note in sequence:
        if sequence.index(note) == len(sequence) - 1:
            break
        next_note = sequence[sequence.index(note) + 1]
        if isinstance(note, Break) and isinstance(next_note, Note):
            if next_note.lyric[0].isupper():
                next_note.lyric = " " + next_note.lyric



scrape_song()

# trim_long_notes()
trim_overlapping_notes()
# merge_letter_polish_lyrics('w')
# merge_letter_polish_lyrics('z')
# add_breaks()
# trim_notes_close_to_breaks()

# fix_capitalized_syllables()
reconstruct_song('')
print("Done!")

# roll_lyrics_right ABANDONED FOR NOW