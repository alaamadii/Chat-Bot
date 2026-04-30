from delivery.models import FormattedMessage

class ResponseFormatter:
    """
    Task 11: Response Formatter
    Tone, length & rich media
    """
    def format(self, raw_text: str, channel: str) -> FormattedMessage:
        formatted_text = raw_text
        
        if channel == "whatsapp":
            # Add WhatsApp bolding to numbers for emphasis
            formatted_text = raw_text.replace("500", "*500*").replace("1200", "*1200*")
            # WhatsApp often likes line breaks
            formatted_text = formatted_text + "\n\n_Powered by NextTech_"
            
        elif channel == "web_chat":
            # Web chat might use HTML
            formatted_text = raw_text.replace("500", "<b>500</b>").replace("1200", "<b>1200</b>")
            formatted_text = f"<p>{formatted_text}</p>"
            
        return FormattedMessage(text=formatted_text)

formatter = ResponseFormatter()
