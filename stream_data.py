# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import sys
import logging
import socketserver
from http import server
from http import HTTPStatus
from threading import Condition
from typing import List
from pathlib import Path

import picamera


PAGE = Path("index.html").read_text(encoding='utf-8')


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition_var = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition_var:
                self.frame = self.buffer.getvalue()
                self.condition_var.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    # handle http GET request
    def do_GET(self):
        # http://raspberrypy.local:8000/
        if self.path == '/':
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)

            self.send_header('Location', '/index.html')

            self.end_headers()
        # http://raspberrypy.local:8000/index.html
        elif self.path == '/index.html':
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(PAGE))

            self.end_headers()
            self.wfile.write(PAGE)
        # http://raspberrypy.local:8000/stream.mjpg
        elif self.path == '/stream.mjpg':
            self.send_response(HTTPStatus.OK)

            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type',
                             'multipart/x-mixed-replace; boundary=FRAME')

            self.end_headers()
            try:
                while True:
                    with output_stream.condition_var:
                        output_stream.condition_var.wait()
                        frame = output_stream.frame
                    self.wfile.write(b'--FRAME\r\n')

                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s',
                                self.client_address, str(e))
        # bad url request
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# def launch_http_server():
with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output_stream = StreamingOutput()
    # Uncomment the next line to change your Pi's Camera rotation (in degrees)
    # camera.rotation = 90
    camera.start_recording(output_stream, format='mjpeg')
    try:
        address = ('', 8000)  # http port = 8000
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()


# def main(args: List[str]):
#     return


# if __name__ == "__main__":
#     main(sys.argv)
