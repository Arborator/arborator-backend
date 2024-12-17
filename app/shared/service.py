import io


class SharedService:
    @staticmethod
    def get_sendable_data(text_content):
        """Send data in file format

        Args:
            text_content (str)

        Returns:
            sendable_data(File)
        """
        sendable_data = io.BytesIO()
        sendable_data.write(text_content.encode("utf-8"))
        sendable_data.seek(0)

        return sendable_data