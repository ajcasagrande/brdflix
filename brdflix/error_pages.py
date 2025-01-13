import cherrypy

import brdflix
import mailer
import settings

def _500(status, message, traceback, version):
    """ Error page for 500 Internal Server Error """
    if brdflix.IS_BETA:
        print traceback
    try:
        if cherrypy.request.user is None or not cherrypy.request.user.group.admin_rights:
            # Email all admins about this is enabled
            if settings.EMAIL.alert_on_500:
                mailer.send_to_admin('BRDFlix {0}'.format(status), 'Message: {0}\n\n{1}'.format(message, traceback))
            return "Error %s. Admins have been emailed regarding this issue." % status
        else:
            return "<pre>Error {0}. {1}\n\n{2}</pre>".format(status, message, traceback)
    except:
        return "Error %s. Please notify website admin." % status

def _403(status, message, traceback, version):
    """ Error page for 403 Forbidden """
    return "<pre>{0}</pre>".format(status)

def _503(status, message,traceback, version):
    return brdflix.XBMC_INTERFACE.error()
