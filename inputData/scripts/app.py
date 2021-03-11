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
    
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8000)))
