    def __init__(self):
        self.application = None
        self.notification_users: Set[int] = set()
        self.user_states = {}  # Store user states for various operations
        self.message_manager = MessageManager(db)  # Initialize message manager
        self.single_message_decorator = SingleMessageDecorator(self.message_manager)
        self.single_message_state = SingleMessageState(self.message_manager)
