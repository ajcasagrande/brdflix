var KEY_ESCAPE = 27;
var KEY_SPACE = 32;
var KEY_LEFT = 37;
var KEY_UP = 38;
var KEY_RIGHT = 39;
var KEY_DOWN = 40;

function smooth_scroll(what){
    $("body").animate({scrollTop: $(what).offset().top});
}

String.prototype.format = function (args) {
    var str = this;
    return str.replace(String.prototype.format.regex, function(item) {
        var intVal = parseInt(item.substring(1, item.length - 1));
        var replace;
        if (intVal >= 0) {
            replace = args[intVal];
        } else if (intVal === -1) {
            replace = "{";
        } else if (intVal === -2) {
            replace = "}";
        } else {
            replace = "";
        }
        return replace;
    });
};
String.prototype.format.regex = new RegExp("{-?[0-9]+}", "g");

function getData(obj, name){
    return obj.getAttribute("data-" + name);
}

function getBool(obj, name){
    return getData(obj, name) == "True";
}

function getInt(obj, name){
    return parseInt(getData(obj, name));
}

function getFloat(obj, name){
    return parseFloat(getData(obj, name));
}

function getPrettyTime(seconds){
    var pos = Math.floor(seconds);
    var minutes = Math.round(pos / 60);
    var seconds = pos % 60;

    var result = minutes + ":";
    if (seconds < 10) {
        result += "0";
    }
    result += seconds;
    return result;
}

function performScan(){
    $.getJSON('/xbmc/performScan', function(data) {
        var res = data.res.status;
        if (res == "OK") {
            $.pnotify({
                title: 'Success',
                text: 'XBMC Library Scan was a success',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'XBMC Library Scan was a failure.\nResult: ' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function setEpisodeWatched(id, new_status){
    var url = '/xbmc/setEpisodeWatched?episodeid='+id+'&watched='+new_status;
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            $.pnotify({
                title: 'Success',
                text: 'New episode status was set successfully.',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'New episode status was not set.\nResult: ' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function setMovieWatched(id, new_status){
    var url = '/xbmc/setMovieWatched?movieid='+id+'&watched='+new_status;
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            $.pnotify({
                title: 'Success',
                text: 'New movie status was set successfully.',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'New movie status was not set.\nResult: ' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function addFavoriteShow(xbmc_id){
    var url='/user/addFavoriteShow?xbmc_id='+xbmc_id;
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            var fave = document.getElementById("btn_favorite");
            if (fave){
                fave.innerText = "Remove from Favorites";
                fave.onclick = function() { removeFavoriteShow(xbmc_id) };
            }
            $.pnotify({
                title: 'Success',
                text: 'Added show to favorites.',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'Could not add show to favorites.\nResult: \n' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function removeFavoriteShow(xbmc_id){
    var url='/user/removeFavoriteShow?xbmc_id='+xbmc_id;
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            var fave = document.getElementById("btn_favorite");
            if (fave){
                fave.innerText = "Add to Favorites";
                fave.onclick = function() { addFavoriteShow(xbmc_id) };
            }
            $.pnotify({
                title: 'Success',
                text: 'Removed show from favorites.',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'Could not remove show from favorites.\nResult: \n' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function modifyFaveNotification(fave_id, notify){
    var url='/user/modifyFaveNotification?id='+fave_id+'&notify='+(notify ? "True" : "False");
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            $.pnotify({
                title: 'Success',
                text: 'success',
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'Result: \n' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function getNextEpisode(tvdb_id){
    url = '/sickbeard/?cmd=show&tvdbid='+tvdb_id;
    $.getJSON(url, function(data) {
        var res = data.data.next_ep_airdate;
        if (res != "") {
            $.pnotify({
                title: data.data.show_name,
                text: 'Next episode: ' + res,
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 10000
            });
        }
    });
}

function setCookie(c_name,value,exdays) {
    var exdate=new Date();
    exdate.setDate(exdate.getDate() + exdays);
    var c_value=escape(value) + ((exdays==null) ? "" : "; expires="+exdate.toUTCString());
    document.cookie=c_name + "=" + c_value;
}

function getCookie(c_name) {
    var i,x,y,ARRcookies=document.cookie.split(";");
    for (i=0;i<ARRcookies.length;i++)
    {
        x=ARRcookies[i].substr(0,ARRcookies[i].indexOf("="));
        y=ARRcookies[i].substr(ARRcookies[i].indexOf("=")+1);
        x=x.replace(/^\s+|\s+$/g,"");
        if (x==c_name)
        {
            return unescape(y);
        }
    }
}

function addResume(popup, user_id, media_id, offset, auto){
    url='/watch/add_resume?user_id={0}&media_id={1}&offset={2}&auto={3}'.format([user_id, media_id, offset, auto]);
    $.getJSON(url, function(data) {
        if (popup){
            var res = data.res.status;
            if (res == "OK") {
                $.pnotify({
                    title: 'Success',
                    text: 'Resume point was added successfully.',
                    type: 'success',
                    styling: 'jqueryui',
                    opacity: 1.0,
                    history: false,
                    delay: 1000
                });
            } else {
                $.pnotify({
                    title: 'Failure',
                    text: 'Resume point was not set.\nResult: ' + res,
                    type: 'error',
                    styling: 'jqueryui',
                    opacity: 1.0,
                    history: false,
                    delay: 2000
                });
            }
        }
    });
}

function xbmc_command(command, server_id){
    var url='/xbmc/'+command+'?server_id='+server_id;
    $.getJSON(url, function(data) {
        var res = data.res.status;
        if (res == "OK") {
            $.pnotify({
                title: 'Success',
                text: 'Result: \n' + res,
                type: 'success',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 1000
            });
        } else {
            $.pnotify({
                title: 'Failure',
                text: 'Result: \n' + res,
                type: 'error',
                styling: 'jqueryui',
                opacity: 1.0,
                history: false,
                delay: 2000
            });
        }
    });
}

function search(query){
    var url = '/search?q=' + encodeURIComponent(query);
    window.location = url;
}

