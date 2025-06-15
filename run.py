#from flask import Flask
#import subprocess
#print("TG")
#app = Flask(__name__)

#@app.route('/run-script')
#def run_script():
#    result = subprocess.run(['python', 'main.py'], capture_output=True, text=True)
#    return f"Output: {result.stdout}"

#app.run(host='0.0.0.0', port=5200)
from flask import Flask, jsonify
import subprocess
import os
from datetime import datetime

app = Flask(__name__)


@app.route('/')
def home():
    return '''
    <h1>Remote Script Runner</h1>
    <p><a href="/run-script">Click here to run main.py</a></p>
    <p><a href="/status">Check status</a></p>
    '''


@app.route('/run-script')
def run_script():
    try:
        print(f"[{datetime.now()}] Running main.py...")
        result = subprocess.run(['python', 'main.py'],
                                capture_output=True,
                                text=True,
                                timeout=60)  # 60 second timeout

        output = f"Exit Code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        print(f"[{datetime.now()}] Script completed with exit code: {result.returncode}")

        return f"<h1>Script Results</h1><pre>{output}</pre><p><a href='/'>Back to home</a></p>"

    except subprocess.TimeoutExpired:
        return "<h1>Error</h1><p>Script timed out after 60 seconds</p><p><a href='/'>Back to home</a></p>"
    except Exception as e:
        return f"<h1>Error</h1><p>Failed to run script: {str(e)}</p><p><a href='/'>Back to home</a></p>"


@app.route('/status')
def status():
    return jsonify({
        'status': 'running',
        'time': datetime.now().isoformat(),
        'working_directory': os.getcwd(),
        'main_py_exists': os.path.exists('main.py')
    })


if __name__ == '__main__':
    print("Starting Flask server...")
    print("Access from iPhone: http://YOUR-MAC-IP:5200")
    print("Local access: http://localhost:5200")
    app.run(host='0.0.0.0', port=5200, debug=True)
