import itertools
import os
from re import S
import itertools
import pickle
from note_seq.chord_symbols_lib import ChordSymbolError
from note_seq.musicxml_parser import ChordSymbol
import numpy as np
import note_seq
from collections import defaultdict

'''
#Carregar e criar lista de objetos de stream
for song in songList:
    score = converter.parse(song)
    k = score.analyze('key')
    i = interval.Interval(k.tonic, pitch.Pitch('C'))
    score = score.transpose(i)
    originalScores.append(score)      

from music21 import instrument

def monophonic(stream):
    try:
        length = len(instrument.partitionByInstrument(stream).parts)
    except:
        length = 0
    return length == 1


#Juntar notas para formar acordes
originalScores = [song.chordify() for song in originalScores]

# obj0, obj1, obj2 are created here...

# Saving the objects:
#with open('/content/drive/My Drive/Colab Notebooks/originalAll2.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
#    pickle.dump(originalScores, f)

# Getting back the objects:
with open('data/originalAll.pkl', 'rb') as f:  # Python 3: open(..., 'rb')
    originalScores = pickle.load(f)

from music21 import note, chord

#Define listas de listas vazias
originalChords = [[] for _ in originalScores]
originalDurations = [[] for _ in originalScores]
originalKeys = []

#Extrai notas, acordes, durações e tonalidades
for i, song in enumerate(originalScores):
    originalKeys.append(str(song.analyze('key')))
    for element in song:
        if isinstance(element, note.Note):
            originalChords[i].append(element.pitch)
            originalDurations[i].append(element.duration.quarterLength)
        elif isinstance(element, chord.Chord):
            originalChords[i].append('.'.join(str(n) for n in element.pitches))
            originalDurations[i].append(element.duration.quarterLength) 
        elif isinstance(element, note.Rest):
            originalChords[i].append("<rest>")
            originalDurations[i].append(element.duration.quarterLength)   

# obj0, obj1, obj2 are created here...

# Saving the objects:
with open('data/originalChords.pkl', 'wb') as f:
    pickle.dump(originalChords, f)
with open('data/originalDurations.pkl', 'wb') as f:
    pickle.dump(originalDurations, f)
with open('data/originalKeys.pkl', 'wb') as f:
    pickle.dump(originalKeys, f)

## AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

# Getting back the objects:
with open('data/originalChords.pkl', 'rb') as f:  # Python 3: open(..., 'rb')
    originalChords = pickle.load(f)
with open('data/originalDurations.pkl', 'rb') as f:  # Python 3: open(..., 'rb')
    originalDurations = pickle.load(f)
with open('data/originalKeys.pkl', 'rb') as f:  # Python 3: open(..., 'rb')
    originalKeys = pickle.load(f)

#Concatenação de todos as listas de acordes e durações para um único vetor
#Tamanho das sequências de treinamento
seq_len = 100

music_tokenized = [[c + '_' + str(d) for c,d in zip(s,t)] for s,t in zip(originalChords, originalDurations)]
joined_music_tokenized = []
for i in range(len(music_tokenized[:200])):
  joined_music_tokenized += music_tokenized[i]

clean_music_tokenized = [song.copy() for song in music_tokenized]

#Música tokenizada, mas com a substituição dos tokens com menor frequência por '<unk>'
counter = Counter(joined_music_tokenized)
for i, song in enumerate(clean_music_tokenized):
  for j, element in enumerate(song):
    if(counter[element] < 3): clean_music_tokenized[i][j] = '<unk>'

music_tokenized[201]

#Acordes e durações únicas
unique = np.unique([element for song in clean_music_tokenized for element in song])

token_to_int = {c : i for i, c in enumerate(unique)}
int_to_token = {i : c for i, c in enumerate(unique)}

#Imprime o número de notas e acordes únicos
print(len(unique))

# Create training examples / targets
X = []
Y = []

for song in clean_music_tokenized:
  for i in range(len(song)-seq_len):
    X.append([token_to_int[c] for c in song[i: i+seq_len]])
    Y.append([token_to_int[c] for c in song[i+1 : i+1+seq_len]]) 

#Definição dos tamanhos dos datasets de treino e validação
train_size = round(0.9*(len(X)))
val_size = round(0.1*(len(X)))

assert train_size+val_size == len(X)
'''

# Adapted from https://github.com/magenta/note-seq/blob/master/note_seq/performance_encoder_decoder.py
# and https://github.com/amazon-research/transformer-gan/blob/main/data/performance_event_repo.py
class MidiEncoder():
    def __init__(self, steps_per_sec, num_vel_bins, min_pitch, max_pitch, stretch_factors=[1.0], pitch_transpose_range=[0]):
        self.steps_per_sec = steps_per_sec
        self.num_vel_bins = num_vel_bins
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch

        self.events_to_ids = self.make_vocab()
        self.ids_to_events = {value: key for key, value in self.events_to_ids.items()}
        self.vocab_size = len(self.events_to_ids)
        
        self.strech_factors = stretch_factors
        self.transpose_amounts = list(range(pitch_transpose_range[0],
                                     pitch_transpose_range[-1]+1))
        
        self.augment_params = [(s, t) for s in self.strech_factors for t in self.transpose_amounts]
        
    def make_vocab(self):
        vocab = defaultdict(list)
        items = 0
        for note in range(self.min_pitch, self.max_pitch + 1):
            vocab[f"NOTE_ON_{note}"] = items
            items+=1
        for note in range(self.min_pitch, self.max_pitch + 1):
            vocab[f"NOTE_OFF_{note}"] = items
            items+=1
        for shift in range(1, self.steps_per_sec+1):
            vocab[f"TIME_SHIFT_{shift}"] = items
            items+=1
        for vel in range(1, self.num_vel_bins+1):
            vocab[f"VELOCITY_{vel}"] = items
            items+=1
        return dict(vocab)

    def filter_pitches(self, note_sequence):
        note_list = []
        deleted_note_count = 0
        end_time = 0
        for note in note_sequence.notes:
            if self.min_pitch <= note.pitch <= self.max_pitch:
                end_time = max(end_time, note.end_time)
                note_list.append(note)
            else:
                deleted_note_count += 1
        
        if deleted_note_count >= 0:
            del note_sequence.notes[:]
            note_sequence.notes.extend(note_list)
        note_sequence.total_time = end_time
        
    def encode_midi_file(self, midi_file, strech_factor=1, transpose_amount=0):
        note_sequence = note_seq.midi_file_to_note_sequence(midi_file)
        note_sequence = note_seq.apply_sustain_control_changes(note_sequence)
        del note_sequence.control_changes[:]

        self.filter_pitches(note_sequence)

        if strech_factor != 1 or transpose_amount != 0:
            note_sequence = self.augment(note_sequence, strech_factor, transpose_amount)
        encoded_performance = self.encode_note_sequence(note_sequence)
        
        return encoded_performance
    
    def encode_note_sequence(self, note_sequence):
        quantized_seq = note_seq.quantize_note_sequence_absolute(note_sequence, self.steps_per_sec)
                
        performance = note_seq.Performance(quantized_seq, num_velocity_bins=self.num_vel_bins)
        
        encoded_performance = self.encode_performance(performance)

        return encoded_performance

    def encode_performance(self, performance):
        encoded_performance = []
        for event in performance:
            event_name=None
            if event.event_type == note_seq.PerformanceEvent.NOTE_ON:
                event_name = f"NOTE_ON_{event.event_value}"
            if event.event_type == note_seq.PerformanceEvent.NOTE_OFF:
                event_name = f"NOTE_OFF_{event.event_value}"
            if event.event_type == note_seq.PerformanceEvent.TIME_SHIFT:
                event_name = f"TIME_SHIFT_{event.event_value}"
            if event.event_type == note_seq.PerformanceEvent.VELOCITY:
                event_name = f"VELOCITY_{event.event_value}"
            
            if event_name:
                encoded_performance.append(self.events_to_ids[event_name])
            else: 
                raise ValueError(f"Unknown event type: {event.event_type} at position {len(performance)}")
        
        return encoded_performance
    
    def decode_to_performance(self, encoded_performance):
        decoded_performance = note_seq.Performance(quantized_sequence=None,
        steps_per_second=self.steps_per_sec, num_velocity_bins=self.num_vel_bins)
        
        #INCUDE?
        '''
        tokens = []
        
        for i, event_id in enumerate(encoded_performance):
            if len(tokens) >= 2 and self.ids_to_events[tokens[-1]] == 'TIME_SHIFT_100' and self.ids_to_events[event_id] == 'TIME_SHIFT_100':
                continue
            tokens.append(event_id)
        '''

        for id in encoded_performance:
            try:
                event_name = self.ids_to_events[id]
                event_splits = event_name.split('_')
                event_type, event_value = '_'.join(event_splits[:-1]), int(event_splits[-1])
                if event_type == 'NOTE_ON':
                    event = note_seq.PerformanceEvent(
                            event_type = note_seq.PerformanceEvent.NOTE_ON, event_value=event_value)
                if event_type == 'NOTE_OFF':
                    event = note_seq.PerformanceEvent(
                            event_type = note_seq.PerformanceEvent.NOTE_OFF, event_value=event_value)
                if event_type == 'TIME_SHIFT':
                    event = note_seq.PerformanceEvent(
                            event_type = note_seq.PerformanceEvent.TIME_SHIFT, event_value=event_value)
                if event_type == 'VELOCITY':
                    event = note_seq.PerformanceEvent(
                            event_type = note_seq.PerformanceEvent.VELOCITY, event_value=event_value)
                    
                decoded_performance.append(event)
            except:
                raise ValueError("Unknown event index: %s" % id)
        return decoded_performance

    def decode_to_note_sequence(self, encoded_performance):
        decoded_performance = self.decode_to_performance(encoded_performance)
        note_sequence = decoded_performance.to_sequence(max_note_duration=3)
        return note_sequence

    def decode_to_midi_file(self, encoded_performance, save_path):
        note_sequence = self.decode_to_note_sequence(encoded_performance)
        note_seq.note_sequence_to_midi_file(note_sequence, save_path)

    def augment(self, note_sequence, stretch_factor, transpose_amount):
        augmented_note_sequence = note_seq.sequences_lib.stretch_note_sequence(note_sequence,
                                    stretch_factor, in_place=False)
        
        try: 
            _, num_deleted_notes = note_seq.sequences_lib.transpose_note_sequence(
                    augmented_note_sequence, transpose_amount,
                    min_allowed_pitch = self.min_pitch, max_allowed_pitch=self.max_pitch,
                    in_place=True
            )
        except ChordSymbolError:
            print('Transposition of chord symbol(s) failed.')
        if num_deleted_notes:
            print('Transposition caused out-of-range pitch(es)')
        return augmented_note_sequence 

    def encode_midi_list(self, midi_list, pkl_path=None):
        encoded_sequences = {'ids':[], 'sequences': []}
        for midi_file in midi_list:
            print(midi_file)
            root, ext = os.path.splitext(os.path.basename(midi_file))
            for sf, ta in self.augment_params:
                encoded_sequences['ids'].append(root + '_' + str(sf) + '_' + str(ta) + ext)
                encoded_sequence = self.encode_midi_file(midi_file, sf, ta)
                encoded_sequences['sequences'].append(encoded_sequence)
        
        if pkl_path is not None:
            with open(pkl_path, 'wb') as handle:
                pickle.dump(encoded_sequences, handle, protocol=pickle.HIGHEST_PROTOCOL)
        return encoded_sequences



    

        
