function performRestart(){
    url = '/admin/restart_json'
    jQuery.getJSON(url, function(data) {
        var res = data.res;
        if (res == "OK") {
            jQuery.pnotify({
                title: 'Success',
                text: 'Performing restart',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            jQuery.pnotify({
                title: 'Failure',
                text: 'Could not perform restart.\nResult: ' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}
