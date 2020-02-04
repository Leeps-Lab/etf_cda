
class InvalidMessageError(Exception):
    pass

def _validate_msg(field_types, msg):
    for field_name, field_type in field_types.items():
        if field_name not in msg or type(msg[field_name]) is not field_type:
            raise InvalidMessageError()

def validate_enter(enter_msg):
    field_types = {
        'price': int,
        'is_bid': bool,
        'pcode': str,
        'asset_name': str,
    }
    _validate_msg(field_types, enter_msg)

def validate_cancel(enter_msg):
    field_types = {
        'price': int,
        'is_bid': bool,
        'pcode': str,
        'asset_name': str,
        'order_id': int,
    }
    _validate_msg(field_types, enter_msg)
