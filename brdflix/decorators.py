import brdflix

def log_request(fn):
    return _set_cp_config(fn, 'tools.log_request.on', True)

def disable_log_request(fn):
    return _set_cp_config(fn, 'tools.log_request.on', False)

def login_required(fn):
    return _set_cp_config(fn, 'tools.login_required.on', True)

def disable_login(fn):
    return _set_cp_config(fn, 'tools.login_required.on', False)

def _set_cp_config(fn, key, val):
    if not hasattr(fn, '_cp_config'):
        fn._cp_config = {}
    fn._cp_config[key] = val
    return fn

def admin_only(fn):
    fn = _set_cp_config(fn, 'tools.login_required.on', True)
    return _set_cp_config(fn, 'tools.login_required.admin_only', True)

def disable_admin_only(fn):
    fn = _set_cp_config(fn, 'tools.login_required.on', True)
    return _set_cp_config(fn, 'tools.login_required.admin_only', False)
