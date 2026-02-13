
class MenuButton:
    def __init__(self, id, text, image, action, cancel_close=False):
        self.id = id
        self.text = text
        self.image = image
        self.action = action 
        self.label = None 
        self.bind_down_event = None 
        self.bind_up_event = None 
        self.is_active = False
        self.cancel_close = cancel_close