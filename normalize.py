import os, configparser, copy

c = configparser.ConfigParser()

c.read(os.path.abspath('config.ini'))

metadata = []
sequence = []
amount_of_breaks = 0
try:
    easy_mode = c["Default"]["easy_mode"].lower() == 'true'
except:
    print("Can't read the config file, you're most likely in the wrong directory!")
    print("Restart the program in the correct directory or fix your config file.")
    # exit the program after the user presses enter, so they have time to read the message
    input("Press enter to exit.")
    exit(0)

if not easy_mode:
    multiplier = float(c["Config"]["multiplier"])
    notegap = int(c["Config"]['notegap']) * multiplier # Best keep this a power of 2 or 5 * x, default 16
    careful_notegap = int(c['Config']['notegap']) * multiplier * float(c["Other"]['careful_notegap_multiplier']) # default 8
else: 
    multiplier = 1
    notegap = 16
    careful_notegap = 8


careful_notegap_length = float(c["Other"]["careful_notegap_length"])
longest_note_length = int(c["Other"]["longest_note_length"])
note_spacing = int(c["Other"]["note_spacing"])
aggressive_note_spacing = False
shortest_note_length = int(c['Other']['shortest_note_length'])

song_path = c['METADATA']['songs_folder_path']
filename = c['METADATA']['filename']
language = c["METADATA"]["language"]
overwrite_file = c["Config"]["overwrite_file"].lower() == 'true'

if_trim_long = c["Config"]["trim_long_notes"].lower() == 'true'
if_lengthen_short = c["Config"]["lengthen_short_notes"].lower() == 'true'

even_breaks = c["Other"]["even_breaks"].lower() == 'true' # False to disable first_note_timestamp
if even_breaks:
    careful_notegap = careful_notegap
first_note_offset = int(c["Other"]["even_breaks_first_note_offset"])
even_note_timestamp_start_template = 0 - first_note_offset
even_breaks_measure = int(c['Other']['even_breaks_measure']) * multiplier # default 64



class Note:
    def __init__(self, timestamp, length, pitch, lyric, type = ':'):
        self.timestamp = timestamp
        self.length = length
        self.pitch = pitch
        self.lyric = lyric
        self.type = type
class Break:
    def __init__(self, timestamp):
        self.timestamp = timestamp

def scrape_song():

    global filename
    if filename == '':
        filename = input("Enter filename: ")
    global path
    path = os.path.join(song_path, filename, filename + ".txt")
    while not os.path.exists(path):
        print(f"Can't find the file {filename}.txt in the folder {os.path.join(song_path, filename)}!")
        print("Make sure the file is in the correct folder and that the filename in the config is correct.")
        input("Press enter to try again.")
    file = open(path, "r", encoding='utf-8')
    lines = file.readlines()
    if overwrite_file:
        # create a new backup file
        with open(os.path.join(song_path, filename, "backup.txt"), "w", encoding='utf-8') as backup:
            for line in lines:
                backup.write(line)
    for line in lines:
        indicator = line[0]
        if indicator == "#":
            metadata.append(line)
        elif indicator == "-":
            # add a new break to the note sequence
            sequence.append(Break(int(line.split()[1])))
        elif indicator == "E" or indicator == "":
            pass
        else:
            a = line.split(" ", 4)
            note = Note(int(a[1]), int(a[2]), int(a[3]), a[4].replace("\n", ""), indicator)
            sequence.append(note)

def reconstruct_song(new_filename = filename):
    global path
    global amount_of_breaks
    if overwrite_file:
        os.remove(path)
        file = open(path, "w", encoding='utf-8')
        new_filename = filename
    else:
        file = open(os.path.join(song_path, filename, new_filename + ".txt"), "w", encoding='utf-8')
    for line in metadata:
        file.write(line)
    for note in sequence:
        if isinstance(note, Break):
            file.write(f"- {note.timestamp}\n")
        else:
            file.write(f"{note.type} {note.timestamp} {int(note.length)} {int(note.pitch)} {note.lyric}\n")
    file.write("E\n")
    
    print(f"For {new_filename} added {amount_of_breaks} breaks.")
    print("Done!")

def trim_long_and_lengthen_short_notes():
    for note in sequence:
        if if_trim_long:
            if isinstance(note, Note) and note.length > longest_note_length:
                note.length = longest_note_length
        if if_lengthen_short:
            if isinstance(note, Note) and note.length < shortest_note_length:
                note.length = shortest_note_length

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
    global even_note_timestamp_start_template
    global even_note_timestamp_start
    global amount_of_breaks
    amount_of_breaks = 0
    even_note_timestamp_start = even_note_timestamp_start_template

    def sequence_insert_break(index, future_break):
        global even_note_timestamp_start
        global amount_of_breaks
        if not even_breaks:
            sequence.insert(index, future_break)
            amount_of_breaks += 1
        else:
            closest_break_timestamp = find_timestamp_of_closest_past_gap(future_break.timestamp)
            while closest_break_timestamp > even_note_timestamp_start:
                even_note_timestamp_start += even_breaks_measure
            if even_note_timestamp_start - 2 < future_break.timestamp:
                sequence.insert(index, future_break)
                even_note_timestamp_start += even_breaks_measure
                amount_of_breaks += 1
                

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

                    if potential_break.timestamp - closest_timestamp - note.length >= careful_notegap * careful_notegap_length:
                        sequence_insert_break(sequence.index(next_note), potential_break)                       

def find_timestamp_of_closest_past_gap(timestamp):
    closest_timestamp = 0
    for note in sequence[::-1]:
        if isinstance(note, Break):
            if note.timestamp < timestamp:
                closest_timestamp = note.timestamp
                return closest_timestamp
    return closest_timestamp

def additional_function(mode, additional_data = ''):
    global sequence
    def function_delete_breaks():
        for note in sequence:
            if isinstance(note, Break):
                sequence.remove(note)
    def scale_sequence():
        if additional_data:
            scale_multiplier = additional_data
        else:
            scale_multiplier = 2
        for note in sequence:
            note.timestamp = note.timestamp * scale_multiplier
            if not isinstance(note, Break):
                note.length = note.length * scale_multiplier

    match mode:
        case 'delete_breaks':
            function_delete_breaks()
        case 'scale_sequence':
            scale_sequence()
        
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

def add_breaks_and_finish():
    add_breaks()
    # trim_notes_close_to_breaks()
    reconstruct_song(f'{amount_of_breaks} notegap {notegap} - {filename}')

scrape_song()

trim_long_and_lengthen_short_notes()
trim_overlapping_notes()

# merge_letter_polish_lyrics('w')
# merge_letter_polish_lyrics('z')
# additional_function('scale_sequence')

# reconstruct_song(f'{amount_of_breaks} notegap {notegap} - {filename}')
# exit(0)


if not easy_mode:
    add_breaks_and_finish()
else:
    initial_sequence = copy.deepcopy(sequence)
    add_breaks_and_finish()
    
    sequence = copy.deepcopy(initial_sequence)
    multiplier = 2
    notegap = 32
    careful_notegap = 16
    add_breaks_and_finish()

    sequence = copy.deepcopy(initial_sequence)
    multiplier = 0.5
    notegap = 8
    careful_notegap = 4
    add_breaks_and_finish()

    sequence = copy.deepcopy(initial_sequence)
    multiplier = 1
    notegap = 10
    careful_notegap = 5
    add_breaks_and_finish()

    sequence = copy.deepcopy(initial_sequence)
    multiplier = 2
    notegap = 20
    careful_notegap = 10
    add_breaks_and_finish()

    sequence = copy.deepcopy(initial_sequence)
    multiplier = 0.5
    notegap = 5
    careful_notegap = 2.5
    add_breaks_and_finish()

input("Done! Press enter to exit.")

# roll_lyrics_right ABANDONED FOR NOW