from threading import Thread
import smtplib
from email.mime.text import MIMEText

import brdflix
from datatypes import *
import settings

def send_to_admin(subject, body, is_html=False):
    """
    Sends a copy of this email to every admin
    that is set to 'allow_email'. Useful for
    logging errors and unauthorized access.
    """
    users = User().query_all()
    for user in users:
        if user.allow_email and user.group.admin_rights:
            send(user.email, subject, body, is_html)

def send(to, subject, body, is_html=False):
    """
    Send an email to someone, using the email account
    defined in settings.
    """
    if settings.EMAIL.enabled:
        msg = MIMEText(body, 'html' if is_html else 'plain')
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL.email
        msg['To'] = to

        # Send mail in another thread to prevent blocking
        thread = Thread(target=_send_thread, args=[msg])
        thread.daemon = True
        thread.start()

def _send_thread(msg):
    """
    The actual sending of an email. This is to be called
    from a separate thread as to prevent blocking.
    """
    server = None
    if settings.EMAIL.provider.lower() == "gmail":
        server = smtplib.SMTP('smtp.gmail.com:587')
    if server is not None:
        #server.set_debuglevel(True)
        server.starttls()
        server.login(settings.EMAIL.email, settings.EMAIL.password)
        try:
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        finally:
            server.quit()
