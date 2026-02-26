
class MusicObject:
    def __init__(self, state, title, artist, channel, album, album_art_api_url, album_art_music_assistant_url=None):
        self.state = state
        self.title = title
        self.artist = artist 
        self.channel = channel 
        self.album = album 
        self.album_art_api_url = album_art_api_url 
        self.album_art_music_assistant_url = album_art_music_assistant_url
