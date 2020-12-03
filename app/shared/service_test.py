from io import BytesIO
from .service import SharedService

text_content_test = "this is a test content"


def test_get_sendable_data():
    sendable_data = SharedService.get_sendable_data(text_content_test)
    assert type(sendable_data) == BytesIO