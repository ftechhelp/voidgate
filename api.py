#!/usr/bin/env python3

import http.server
import socketserver
import json
import subprocess
import urllib.parse
import os
from urllib.parse import urlparse

# Configuration from environment variables with defaults
API_PASSWORD = os.environ.get('VOIDGATE_PASSWORD', 'playground_voidgate')
HOST_IP = os.environ.get('VOIDGATE_HOST', '172.17.0.1')

class CommandHandler(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
        if self.path == '/execute':
            self.handle_execute()
        elif self.path == '/run_script':
            self.handle_run_script()
        else:
            self.send_error(404, "Not Found")
    
    def do_GET(self):
        if self.path == '/health':
            self.handle_health()
        else:
            self.send_error(404, "Not Found")
    
    def handle_execute(self):
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length == 0:
                self.send_json_response({'error': 'No data provided'}, 400)
                return
            
            # Read and parse JSON data
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'error': 'Invalid JSON'}, 400)
                return
            
            # Check authentication
            if data.get('password') != API_PASSWORD:
                self.send_json_response({'error': 'Invalid password'}, 401)
                return
            
            # Get command from request
            command = data.get('command')
            if not command:
                self.send_json_response({'error': 'No command provided'}, 400)
                return
            
            # Execute command
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                # Return result
                response = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode,
                    'success': result.returncode == 0
                }
                self.send_json_response(response, 200)
                
            except subprocess.TimeoutExpired:
                self.send_json_response({'error': 'Command timed out after 30 seconds'}, 408)
                
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_run_script(self):
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length == 0:
                self.send_json_response({'error': 'No data provided'}, 400)
                return
            
            # Read and parse JSON data
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'error': 'Invalid JSON'}, 400)
                return
            
            # Check authentication
            if data.get('password') != API_PASSWORD:
                self.send_json_response({'error': 'Invalid password'}, 401)
                return
            
            # Get script path from request
            script_path = data.get('script_path')
            if not script_path:
                self.send_json_response({'error': 'No script_path provided'}, 400)
                return
            
            # Validate that path is absolute
            if not os.path.isabs(script_path):
                self.send_json_response({'error': 'Script path must be absolute'}, 400)
                return
            
            # Check if file exists
            if not os.path.exists(script_path):
                self.send_json_response({'error': f'Script file not found: {script_path}'}, 404)
                return
            
            # Check if file is readable
            if not os.access(script_path, os.R_OK):
                self.send_json_response({'error': f'Script file not readable: {script_path}'}, 403)
                return
            
            # Get optional arguments
            args = data.get('args', [])
            if not isinstance(args, list):
                self.send_json_response({'error': 'Args must be a list'}, 400)
                return
            
            # Get optional working directory
            working_dir = data.get('working_dir')
            if working_dir and not os.path.isabs(working_dir):
                self.send_json_response({'error': 'Working directory must be absolute path'}, 400)
                return
            
            # Build command
            cmd = [script_path] + args
            
            # Execute script
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=working_dir
                )
                
                # Return result
                response = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode,
                    'success': result.returncode == 0,
                    'script_path': script_path,
                    'args': args,
                    'working_dir': working_dir
                }
                self.send_json_response(response, 200)
                
            except subprocess.TimeoutExpired:
                self.send_json_response({'error': 'Script timed out after 30 seconds'}, 408)
                
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_health(self):
        self.send_json_response({'status': 'healthy'}, 200)
    
    def send_json_response(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        # Override to reduce verbose logging
        pass

def run_server(port=5000):
    print("⚠️  WARNING: This API allows arbitrary command execution!")
    print("⚠️  Only use in isolated, controlled environments!")
    print("⚠️  Never expose this to the internet!")
    print()
    print(f"Starting API server on http://{HOST_IP}:{port}")
    print("Available endpoints:")
    print("  POST /execute    - Execute commands")
    print("  POST /run_script - Run script from absolute path")
    print("  GET  /health     - Health check")
    print()
    
    with socketserver.TCPServer((HOST_IP, port), CommandHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()

if __name__ == '__main__':
    run_server()
