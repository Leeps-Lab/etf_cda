from collections import Iterable

NoneType = type(None)

class InvalidMessageError(Exception):
    def __init__(self, message_name, field_name, field_type):
        self.message_name = message_name
        self.field_name = field_name
        self.field_type = field_type
    
    def __str__(self):
        return 'incoming message validation failed: {} message should have a field "{}" of type "{}"'.format(
            self.message_name, self.field_name, self.field_type.__name__
        )

def _check_type(field_type, expected_type):
    if isinstance(expected_type, Iterable):
        return field_type in expected_type
    else:
        return field_type is expected_type

def _validate_msg(field_types, msg, message_name):
    for field_name, field_type in field_types.items():
        if field_name not in msg or not _check_type(type(msg[field_name]), field_type):
            raise InvalidMessageError(message_name, field_name, field_type)

ORDER_TYPES = {
    'timestamp': float,
    'price': int,
    'volume': int,
    'is_bid': bool,
    'pcode': str,
    'traded_volume': (int, NoneType),
    'order_id': int,
    'asset_name': str,
}

def validate_enter(enter_msg):
    field_types = {
        'price': int,
        'volume': int,
        'is_bid': bool,
        'pcode': str,
        'asset_name': str,
    }
    _validate_msg(field_types, enter_msg, 'enter')

def validate_cancel(cancel_msg):
    _validate_msg(ORDER_TYPES, cancel_msg, 'cancel')

def validate_accept_immediate(accept_msg):
    _validate_msg(ORDER_TYPES, accept_msg, 'accept')
