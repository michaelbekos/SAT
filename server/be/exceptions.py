class IdRelatedException(Exception):
    """
    This is a wrapper exception to conserve the information about the processed id.
    """

    def __init__(self, entity_id, message):
        self.entity_id = entity_id
        self.message = message
