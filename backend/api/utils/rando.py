import random
import string

def generate_random_data(size=1024):  # Size in bytes
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

with open('input_data.txt', 'w') as f:
    f.write(generate_random_data())
