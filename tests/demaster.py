import re

def clean_title(song_title):
    # Define a regular expression pattern to match common unwanted text
    pattern = r'\s?(\(.*\)|\[.*\]|-.* remaster(ed).*|-.*anniversary.*|-.*live.*|-.*acoustic.*|-.*remix.*|-.*extended version.*|-.*feat\. .*\b)'

    # Use re.sub to replace the unwanted text with an empty string
    cleaned_title = re.sub(pattern, '', song_title, flags=re.IGNORECASE)

    return cleaned_title

# Example usage:
songs = [
"Titel (poejes)",
"Blondie Singles Collection: 1977-1982",
"Bohemian Rhapsody (Live)",
"Hotel California (Acoustic Version)",
"Imagine - 2019 Remastered",
"Imagine (2019 Remastered)",
"Yesterday (feat. John Lennon)",
"Shape of You - Live at Wembley Stadium",
"Wonderwall (Unplugged)",
"Sweet Child o' Mine - Remastered 2020",
"Rolling in the Deep (Extended Version)",
"Like a Rolling Stone (Live)",
"Purple Haze (Remastered)",
"Yellow Submarine (feat. Ringo Starr)",
"Smooth - Live in San Francisco",
"Billie Jean (Acoustic Cover)",
"Time (Live at Pompeii)",
"Hotel California - 40th Anniversary Edition",
"Hallelujah (feat. Jeff Buckley)",
"Radioactive - Live from T in the Park",
"With or Without You (Live)",
"Wish You Were Here - 2019 Remix",
"Highway to Hell (Live at River Plate)",
"Rolling in the Deep (Piano Version)",
"Purple Haze (Live at Woodstock)",
"Rocket Man (Remastered 2018)",
"Wonderwall - Acoustic Cover",
"Imagine (feat. Yoko Ono)",
"Sweet Child o' Mine - Live in Tokyo",
"Bad Romance (Acoustic)",
"Yesterday - 50th Anniversary Edition",
"Hotel California (Live Unplugged)",
"Let It Be (feat. Paul McCartney)",
"Time - Live at the Dark Side of the Moon",
"Smooth (Extended Remix)",
"Rolling in the Deep - 10th Anniversary",
"Purple Haze (Acoustic)",
"Bohemian Rhapsody - Live Aid Version",
"Rocket Man (feat. Bernie Taupin)",
"Wonderwall - MTV Unplugged",
"Yellow Submarine (Remastered 2015)",
"Like a Rolling Stone (feat. Bob Dylan)",
"Billie Jean - Acoustic Live",
"Hotel California (Live at Hell Freezes Over)",
"Yesterday - Acoustic Version",
"Sweet Child o' Mine (Live at The Roxy)",
"Imagine - Remastered 2017",
"Radioactive (Extended Mix)",
"Purple Haze - Live at Monterey Pop Festival",
"Wish You Were Here (Acoustic)",
"Rocket Man - Remastered 2016",
"Rolling in the Deep (feat. Adele)",
"Time (feat. Pink Floyd)",
]

for song in songs:
    print("===========")
    print(f"Original: {song}")
    print(f"New: {clean_title(song)}")