#!/usr/local/bin/python

from pathlib import Path
from os import path as ospath

from flask import Flask

app = Flask(__name__)

## Every Function/Service Must contain a /ready path. 
## Knative uses this to know when your container is ready to go.
@app.route('/ready')
def ready():
   return 'ready'

@app.route('/')
def index():
    # time.sleep(10)
    return 'Refreshed, for 30 seconds'


if __name__ == "__main__":
    loginToken = apicLogin()

    refreshThread = threading.Thread(target=refresh)
    refreshThread.start()

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://" + config['apic_login']['address'] + "/socket" + loginToken,
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                on_open = on_open)

    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8000)))
