from itd import ITDClient

c = ITDClient(cookies=input('token: '))

with open('ПУТЬ/ДО/ГИФКИ.gif', 'rb') as f:
    file_data = f.read()

file_data = file_data.replace(b'\x00\x3b', b'\xee\x3b') # можно менять "\xff" (диапазон 00-ff, например 9b)
file = c.upload_file('itd-sdk.gif', file_data)
if file.mime_type == 'image/jpeg':
    print('not converted to GIF! Increase replacing value ("\\xff")')
    quit()

print('link', file.url)

c.create_post(
    attachment_ids=[file.id]
)
