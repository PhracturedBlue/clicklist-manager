import time
import re
from cgi import escape
from threading import Thread
import queue
from clicklist_manager import update_cart
import logging
from logging.handlers import QueueHandler
import datetime

logging.basicConfig(level=logging.INFO)
que = queue.Queue(-1)
log_root = logging.getLogger(None)
log_root.addHandler(QueueHandler(que)) 
running = False

class ClickListThread(Thread):
    def __init__(self):
        global running
        Thread.__init__(self)
        running = True
        #queue_handler = QueueHandler(self.que)
        #logging.getLogger().addHandler(queue_handler)

    def run(self):
        global running
        logging.info("Running ClickList update")
        update_cart()
        running = False

def index(environ, start_response):
    """This function will be mounted on "/" and display a link
    to the hello world page."""
    print("Sending Index")
    t = ClickListThread()
    t.daemon = True
    t.start()
    start_response('200 OK', [('Content-Type', 'text/html')])
    str = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
</head>
<body>
  <script>
    var source = new EventSource('/events');
    source.onmessage = function(e) {
      document.body.innerHTML += e.data + '<br>';
    };
  </script>
</body>
</html>'''
    return [str.encode('utf-8')]

def events(environ, start_response):
    if not running:
        start_response('204 No Content', [('Content-Type', 'text/event-stream')]) #('Cache-Control: no-cache')
        return [b'']

    start_response('200 OK', [('Content-Type', 'text/event-stream')]) #('Cache-Control: no-cache')
    #logging.info("Start Event")
    try:
        while True:
            line = que.get(False)
            t = datetime.datetime.fromtimestamp(line.created)
            yield 'data:{} {}: {}\n\n'.format(line.levelname, t.strftime("%Y-%m-%d %H:%M:%S.%f"), line.message).encode('utf-8')
    except:
        pass

def not_found(environ, start_response):
    """Called if no URL matches."""
    start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    return [b'Not Found']

# map urls to functions
urls = [
    (r'^$', index),
    (r'events/?$', events),
]

def application(environ, start_response):
    """
    The main WSGI application. Dispatch the current request to
    the functions from above and store the regular expression
    captures in the WSGI environment as  `myapp.url_args` so that
    the functions from above can access the url placeholders.

    If nothing matches call the `not_found` function.
    """
    path = environ.get('PATH_INFO', '').lstrip('/')
    for regex, callback in urls:
        match = re.search(regex, path)
        if match is not None:
            environ['myapp.url_args'] = match.groups()
            return callback(environ, start_response)
    return not_found(environ, start_response)

    
