import json
import requests #импортируем модуль


adresses_url = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
menu_url = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'






with open('adresses.json', "r", encoding='utf-8') as adresses:
    serialized_adresses = json.load(adresses)


with open('menu.json', "r", encoding='utf-8') as menu:
    serialized_menu = json.load(menu)

print(len(serialized_adresses))
print(len(serialized_menu))