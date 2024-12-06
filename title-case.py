# Open the file in read mode and read its content
with open('creature-words.txt', 'r') as file:
    data = file.read()

# Split the content by lines
lines = data.split('\n')

# For each line, use the title() method to convert it to title case
title_cased_lines = [line.title() for line in lines]

# Join the lines back together
result = '\n'.join(title_cased_lines)

# Open the file in write mode and write the result back to the file
with open('creature-words.txt', 'w') as file:
    file.write(result)