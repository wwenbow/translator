# Import gevent first to patch the environment before importing other modules
# from gevent import monkey
# monkey.patch_all()

from flask import Flask, render_template_string
from flask_socketio import SocketIO
import threading

# Flask app initialization with async_mode specified as "gevent"
app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')

@app.route('/')
def index():
    return render_template_string('''
    <html>
        <head>
            <title>WebSocket Test</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
            <script type="text/javascript">
                var socket = io();

                socket.on('connect', function() {
                    console.log('WebSocket connected!');
                });

                socket.on('refresh', function (msg) {
                    console.log('Refreshing page...');
                    window.location.reload();  // Refresh the page
                });

                function sendRefreshEvent() {
                    socket.emit('test_event', {data: 'Test from client'});
                    console.log('Test event sent to server');
                }
            </script>
        </head>
        <body>
            <h1>WebSocket Test</h1>
            <button onclick="sendRefreshEvent()">Send Refresh Event</button>
        </body>
    </html>
    ''')

@socketio.on('test_event')
def handle_test_event(data):
    print('Received test event from client:', data)
    socketio.emit('refresh', {'data': 'Refreshing the page'}, broadcast=True)

def run_flask_app():
    socketio.run(app, port=5000)

# Start the Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

# Keep the program running to test WebSocket functionality
print("Open http://localhost:5000 in your browser to test WebSocket functionality.")
input("Press Enter to exit...\n")
