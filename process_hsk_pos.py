from typing import List, Dict, Tuple, Set
from pathlib import Path
import nltk
from nltk.corpus import wordnet
import re
import os
import sys
from time import sleep

def download_nltk_data() -> None:
    """Download required NLTK data."""
    print("Setting up NLTK data...")
    
    # Set custom download directory in the project
    nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    # Set the NLTK data path
    nltk.data.path.append(nltk_data_dir)
    
    # Download required data
    for package in ['wordnet', 'averaged_perceptron_tagger']:
        print(f"Downloading {package}...")
        try:
            nltk.download(package, download_dir=nltk_data_dir, quiet=True)
            print(f"Successfully downloaded {package}")
            sleep(1)  # Give some time between downloads
        except Exception as e:
            print(f"Warning: Could not download {package}. Error: {e}")
            print("Will proceed with limited functionality.")
            sleep(1)

def get_wordnet_pos(pos: str) -> str:
    """
    Convert our POS tag to WordNet POS tag.
    
    Args:
        pos: Part of speech tag (noun, verb, adj, adv)
        
    Returns:
        WordNet POS tag
    """
    tag_map = {
        'noun': wordnet.NOUN,
        'verb': wordnet.VERB,
        'adj': wordnet.ADJ,
        'adv': wordnet.ADV
    }
    return tag_map.get(pos, wordnet.NOUN)

def get_synonyms(word: str, pos: str) -> List[str]:
    """
    Get synonyms for a word using WordNet.
    
    Args:
        word: The word to find synonyms for
        pos: Part of speech of the word
        
    Returns:
        List of synonyms
    """
    try:
        # Clean the word - remove parentheses and extra info
        word = re.sub(r'\([^)]*\)', '', word).strip()
        word = word.split(',')[0].split(';')[0].strip().lower()
        
        # Get WordNet POS
        wn_pos = get_wordnet_pos(pos)
        
        # Get synsets
        synsets = wordnet.synsets(word, pos=wn_pos)
        
        # Collect all lemma names
        synonyms: Set[str] = set()
        for synset in synsets[:2]:  # Limit to first 2 synsets to avoid too many synonyms
            for lemma in synset.lemmas():
                if lemma.name() != word and '_' not in lemma.name():
                    synonyms.add(lemma.name())
        
        # Return formatted string of synonyms
        return sorted(list(synonyms)[:3])  # Limit to 3 synonyms
    except Exception as e:
        print(f"Warning: Could not get synonyms for '{word}'. Error: {e}")
        return []

def determine_part_of_speech(definition: str, chinese: str) -> str:
    """
    Determine the part of speech based on the English definition.
    
    Args:
        definition: The English definition of the word
        chinese: The Chinese word (used for additional context)
        
    Returns:
        The determined part of speech (noun, verb, adj, adv, etc.)
    """
    definition = definition.lower()
    
    # Action words/verbs
    if any(x in definition for x in ['do', 'make', 'become', 'handle', 'manage', 'operate', 
                                   'establish', 'publish', 'register', 'turn', 'close', 'shut',
                                   'wave', 'block', 'stop', 'read', 'study', 'train', 'touch',
                                   'approach', 'donate', 'overcome', 'visit', 'lean', 'cut',
                                   'kill', 'delete', 'rise', 'lose', 'absorb', 'imagine',
                                   'modify', 'extend', 'cook', 'prevent']):
        return 'verb'
    
    # Nouns (things, people, places, concepts)
    elif any(x in definition for x in ['person', 'place', 'thing', 'princess', 'engineer', 
                                     'worker', 'aunt', 'officer', 'pipe', 'cd', 'dvd', 
                                     'square', 'counter', 'pot', 'pan', 'king', 'butterfly',
                                     'alley', 'chemistry', 'dust', 'match', 'muscle', 
                                     'family', 'shoulder', 'scissors', 'bell', 'wall',
                                     'circle', 'equipment', 'network', 'system']):
        return 'noun'
    
    # Adjectives (descriptions)
    elif any(x in definition for x in ['high-grade', 'individual', 'fixed', 'classical',
                                     'peaceful', 'sudden', 'slippery', 'intense', 'fierce',
                                     'lonely', 'honest', 'sincere', 'optimistic', 'continuous',
                                     'good', 'fine', 'reliable', 'strong', 'weak', 'soft',
                                     'perfect', 'special', 'modern', 'straight']):
        return 'adj'
    
    # Adverbs
    elif any(x in definition for x in ['especially', 'widely', 'hastily', 'hurriedly',
                                     'actually', 'unexpectedly', 'allegedly', 'personally',
                                     'easily', 'gradually', 'voluntarily']):
        return 'adv'
    
    # Measure words
    elif any(x in definition for x in ['measure word', 'classifier']):
        return 'measure'
    
    # Interjections
    elif any(x in definition for x in ['expressing', 'exclamation']):
        return 'intj'
    
    # Prepositions
    elif any(x in definition for x in ['according to', 'as for', 'by means of']):
        return 'prep'
    
    # Default categorization based on common patterns
    if definition.startswith(('the ', 'a ', 'an ')):
        return 'noun'
    elif '(v.)' in definition or definition.endswith(('ate', 'ize', 'ify')):
        return 'verb'
    elif definition.endswith(('ly', 'wise')):
        return 'adv'
    elif definition.endswith(('ful', 'ous', 'ive', 'able', 'al')):
        return 'adj'
    
    # Default to noun if unclear
    return 'noun'

def process_file(input_file: str, output_file: str) -> None:
    """
    Process the HSK vocabulary file and add part of speech and synonyms information.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
    """
    # Download required NLTK data
    download_nltk_data()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Process header
    header = lines[0].strip()
    if not header.endswith('synonyms'):
        header = header + '|synonyms'
    
    processed_lines = [header]
    
    # Process content lines
    for line in lines[1:]:
        parts = line.strip().split('|')
        if len(parts) < 4:
            continue
            
        number, chinese, pinyin, english = parts[:4]
        pos = determine_part_of_speech(english, chinese)
        synonyms = get_synonyms(english, pos)
        
        # Get synonyms and add them to the English definition if they exist
        if synonyms:
            # Check if the English definition already contains these synonyms
            existing_words = set(w.strip().lower() for w in english.split(','))
            new_synonyms = [s for s in synonyms if s.lower() not in existing_words]
            if new_synonyms:
                english = f"{english}, {', '.join(new_synonyms)}"
        
        # If there are existing fields after English, preserve them
        if len(parts) > 4:
            processed_line = '|'.join(parts[:-1])  # Exclude the last field (old part_of_speech)
        else:
            processed_line = '|'.join(parts)
            
        processed_line += f"|{pos}"
        processed_lines.append(processed_line)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(processed_lines))

if __name__ == '__main__':
    process_file('hsk-with-pos.csv', 'hsk-with-synonyms.csv') 