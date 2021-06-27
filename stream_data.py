# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import logging
import socketserver
import sys
import threading
from http import HTTPStatus, server
from pathlib import Path
from typing import List

import picamera


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition_var = threading.Condition()

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
                    with OUTPUT_STREAM.condition_var:
                        OUTPUT_STREAM.condition_var.wait()
                        frame = OUTPUT_STREAM.frame
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


PAGE = Path("index.html").read_bytes()
OUTPUT_STREAM = StreamingOutput()


def main(args: List[str]):
    with picamera.PiCamera(resolution=args[1], framerate=int(args[2])) as camera:
        # Uncomment the next line to change your Pi's Camera rotation (in degrees)
        # camera.rotation = 90
        camera.start_recording(OUTPUT_STREAM, format='mjpeg')
        try:
            address = ('', 8000)  # http port = 8000
            server = StreamingServer(address, StreamingHandler)
            server.serve_forever()
        finally:
            camera.stop_recording()
    return


if __name__ == "__main__":
    if(len(sys.argv) == 3):
        main(sys.argv)
    else:
        print("Usage: program_name [resolution] [framerate]\n"
              " Resolution example - 640x480")
