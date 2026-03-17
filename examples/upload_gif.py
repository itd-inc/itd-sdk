from itd import ITDClient
from itd.post import Post
from time import sleep
from random import randint

c = ITDClient(input('token: '))

with open('1.gif', 'rb') as f:
    file_data = f.read()

# file_data += b'\xbb\xff\x3b'
# print(file_data)
agreed = False
file = None
length = len(file_data)
while not agreed:
    rnd = randint(length - max(length, 100000), length)
    file = c.upload_file('1.gif', file_data.replace(file_data[rnd:rnd + 3], b'\xff\xff\xff\xbb\x00'))
    if file.mime_type == 'image/jpeg':
        print('not converted to GIF! Try again...')
        sleep(3)
        continue

    print('check this out: ', file.url)
    agreed = input('? ') == 'y'

Post.new('ахахаха', attachment_ids=[file.id])