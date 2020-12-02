import io


class SharedService:
    @staticmethod
    def get_sendable_data(text_content):
        sendable_data = io.BytesIO()
        sendable_data.write(text_content.encode("utf-8"))
        sendable_data.seek(0)

        return sendable_data