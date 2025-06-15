from flask import Flask, jsonify
import subprocess
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>Tennis Court Booking Bot</h1>
    <p><a href="/run-script">🎾 Book Tennis Court</a></p>
    <p><a href="/status">📊 Check Status</a></p>
    '''

@app.route('/run-script')
def run_script():
    try:
        print(f"[{datetime.now()}] Running tennis booking script...")
        result = subprocess.run(['python', 'main.py'],
                                capture_output=True,
                                text=True,
                                timeout=180)  # 3 minutes timeout for booking

        output = f"Exit Code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        print(f"[{datetime.now()}] Script completed with exit code: {result.returncode}")

        return f"<h1>🎾 Tennis Booking Results</h1><pre>{output}</pre><p><a href='/'>Back to home</a></p>"

    except subprocess.TimeoutExpired:
        return "<h1>⏰ Timeout</h1><p>Script timed out after 3 minutes</p><p><a href='/'>Back to home</a></p>"
    except Exception as e:
        return f"<h1>❌ Error</h1><p>Failed to run script: {str(e)}</p><p><a href='/'>Back to home</a></p>"

@app.route('/status')
def status():
    return jsonify({
        'status': 'running',
        'time': datetime.now().isoformat(),
        'working_directory': os.getcwd(),
        'main_py_exists': os.path.exists('main.py')
    })

if __name__ == '__main__':
    # Use Railway's PORT environment variable
    port = int(os.environ.get('PORT', 5200))
    print("Starting Tennis Booking Server...")
    print(f"Running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)