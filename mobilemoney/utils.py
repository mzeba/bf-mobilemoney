from datetime import datetime


def get_reference():
    reference = datetime.now().strftime("%y%m%d.%H%M%S.%f")
    return "eT" + reference
