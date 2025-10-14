# LutrisGamesPatchNotes
Python script with a simple interface that gets a list of all the patch notes of all your games in your Lutris database.

<img width="1895" height="2065" alt="image" src="https://github.com/user-attachments/assets/896fa773-ed0a-4e55-9e1e-7485d239a09b" />

Useful to stay up to date with Steam games in Lutris.

With this script you don't need to go one by one checking all the updates for all your Lutris games.

You can choose a game from the Lutris list loaded in the interface to filter only updates for that game.

The updates list is also written to a txt file.

## Requirements
- Python3
- requests
- beautifulsoup4
- lxml
- python3-tk

```
pip install -r requirements.txt
```
or
```
pip install requests beautifulsoup4 lxml python3-tk
```
## TODO
- Better interface
- Clickable links
- Pictures from links
- Exclude games
- Don't update
