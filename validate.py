
class InvalidMessageError(Exception):
    def __init__(self, message_name, field_name, field_type):
        self.message_name = message_name
        self.field_name = field_name
        self.field_type = field_type
    
    def __str__(self):
        return 'incoming message validation failed: {} message should have a field "{}" of type "{}"'.format(
            self.message_name, self.field_name, self.field_type.__name__
        )

def _validate_msg(field_types, msg, message_name):
    for field_name, field_type in field_types.items():
        if field_name not in msg or type(msg[field_name]) is not field_type:
            raise InvalidMessageError(message_name, field_name, field_type)

def validate_enter(enter_msg):
    field_types = {
        'price': int,
        'volume': int,
        'is_bid': bool,
        'pcode': str,
        'asset_name': str,
    }
    _validate_msg(field_types, enter_msg, 'enter')

def validate_cancel(enter_msg):
    field_types = {
        'price': int,
        'is_bid': bool,
        'pcode': str,
        'asset_name': str,
        'order_id': int,
    }
    _validate_msg(field_types, enter_msg, 'cancel')
