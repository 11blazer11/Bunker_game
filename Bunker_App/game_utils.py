import random
from .charachteristics import (
    get_random_age, gender, heights, professions, hobbies, health, items, special_traits, phobias
)

# Note: special_traits is defined in charachteristics.py


def generate_character():
    """Generate a random character with balanced characteristics."""
    char = {
        'age': get_random_age(),
        'gender': random.choice(gender),
        'height': random.choice(heights),
        'profession': None,
        'hobby': None,
        'health': None,
        'item': None,
        'special_trait': None,
        'phobia': None,
        'all_characteristics': []
    }
    
    # Ensure minimum 2 bad characteristics
    bad_char_count = 0
    
    # Select profession
    if random.random() < 0.6:  # 60% good, 40% bad
        char['profession'] = random.choice(professions['good_chars'])
        char['all_characteristics'].append(('profession', char['profession'], 'good'))
    else:
        char['profession'] = random.choice(professions['bad_chars'])
        char['all_characteristics'].append(('profession', char['profession'], 'bad'))
        bad_char_count += 1
    
    # Select hobby
    if random.random() < 0.6:  # 60% good, 40% bad
        char['hobby'] = random.choice(hobbies['good_chars'])
        char['all_characteristics'].append(('hobby', char['hobby'], 'good'))
    else:
        char['hobby'] = random.choice(hobbies['bad_chars'])
        char['all_characteristics'].append(('hobby', char['hobby'], 'bad'))
        bad_char_count += 1
    
    # Select health
    if random.random() < 0.6:  # 60% good, 40% bad
        char['health'] = random.choice(health['good_chars'])
        char['all_characteristics'].append(('health', char['health'], 'good'))
    else:
        char['health'] = random.choice(health['bad_chars'])
        char['all_characteristics'].append(('health', char['health'], 'bad'))
        bad_char_count += 1
    
    # Select item
    if random.random() < 0.6:  # 60% good, 40% bad
        char['item'] = random.choice(items['good_chars'])
        char['all_characteristics'].append(('item', char['item'], 'good'))
    else:
        char['item'] = random.choice(items['bad_chars'])
        char['all_characteristics'].append(('item', char['item'], 'bad'))
        bad_char_count += 1
    
    # Select special trait
    if random.random() < 0.6:  # 60% good, 40% bad
        char['special_trait'] = random.choice(special_traits['good_chars'])
        char['all_characteristics'].append(('special_trait', char['special_trait'], 'good'))
    else:
        char['special_trait'] = random.choice(special_traits['bad_chars'])
        char['all_characteristics'].append(('special_trait', char['special_trait'], 'bad'))
        bad_char_count += 1
    
    # Select phobia
    if random.random() < 0.4:  # 40% good, 60% bad (phobias are mostly bad)
        char['phobia'] = random.choice(phobias['good_chars'])
        char['all_characteristics'].append(('phobia', char['phobia'], 'good'))
    else:
        char['phobia'] = random.choice(phobias['bad_chars'])
        char['all_characteristics'].append(('phobia', char['phobia'], 'bad'))
        bad_char_count += 1
    
    # Ensure minimum 2 bad characteristics
    if bad_char_count < 2:
        # Need to add more bad characteristics
        bad_needed = 2 - bad_char_count
        characteristic_types = ['profession', 'hobby', 'health', 'item', 'special_trait', 'phobia']
        
        for _ in range(bad_needed):
            # Find characteristics with good values and replace them
            good_characteristics = [
                (i, (char_type, _, quality)) for i, (char_type, _, quality) in enumerate(char['all_characteristics'])
                if quality == 'good'
            ]
            
            if good_characteristics:
                idx, (char_type, _, _) = random.choice(good_characteristics)
                # Replace with bad characteristic
                if char_type == 'profession':
                    char['profession'] = random.choice(professions['bad_chars'])
                elif char_type == 'hobby':
                    char['hobby'] = random.choice(hobbies['bad_chars'])
                elif char_type == 'health':
                    char['health'] = random.choice(health['bad_chars'])
                elif char_type == 'item':
                    char['item'] = random.choice(items['bad_chars'])
                elif char_type == 'special_trait':
                    char['special_trait'] = random.choice(special_traits['bad_chars'])
                elif char_type == 'phobia':
                    char['phobia'] = random.choice(phobias['bad_chars'])
                
                # Update the characteristics list
                char['all_characteristics'][idx] = (char_type, char[char_type], 'bad')
    
    return char
