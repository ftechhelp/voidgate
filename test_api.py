#!/usr/bin/env python3

import unittest
import json
import http.client
import threading
import time
import os
import tempfile
import sys
from pathlib import Path

# Import the server module
import api

class TestVoidgateAPI(unittest.TestCase):
    """Test suite for Voidgate API server"""
    
    @classmethod
    def setUpClass(cls):
        """Start the API server in a background thread before running tests"""
        # Set test password
        os.environ['VOIDGATE_PASSWORD'] = 'test_password'
        os.environ['VOIDGATE_HOST'] = '127.0.0.1'
        
        # Reload the api module to pick up new env vars
        import importlib
        importlib.reload(api)
        
        # Start server in background thread
        cls.server_thread = threading.Thread(target=api.run_server, kwargs={'port': 5001}, daemon=True)
        cls.server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        cls.host = '127.0.0.1'
        cls.port = 5001
        cls.password = 'test_password'
    
    def _make_request(self, method, path, data=None):
        """Helper method to make HTTP requests"""
        conn = http.client.HTTPConnection(self.host, self.port)
        headers = {'Content-Type': 'application/json'} if data else {}
        body = json.dumps(data) if data else None
        
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        conn.close()
        
        try:
            response_json = json.loads(response_data) if response_data else {}
        except json.JSONDecodeError:
            response_json = {}
        
        return response.status, response_json
    
    def test_health_endpoint(self):
        """Test the /health endpoint"""
        status, data = self._make_request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual(data.get('status'), 'healthy')
    
    def test_execute_missing_password(self):
        """Test /execute with missing password"""
        status, data = self._make_request('POST', '/execute', {'command': 'echo test'})
        self.assertEqual(status, 401)
        self.assertIn('error', data)
    
    def test_execute_wrong_password(self):
        """Test /execute with wrong password"""
        status, data = self._make_request('POST', '/execute', {
            'password': 'wrong_password',
            'command': 'echo test'
        })
        self.assertEqual(status, 401)
        self.assertIn('error', data)
    
    def test_execute_missing_command(self):
        """Test /execute with missing command"""
        status, data = self._make_request('POST', '/execute', {'password': self.password})
        self.assertEqual(status, 400)
        self.assertIn('error', data)
    
    def test_execute_simple_command(self):
        """Test /execute with a simple command"""
        status, data = self._make_request('POST', '/execute', {
            'password': self.password,
            'command': 'echo "Hello World"'
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get('success'))
        self.assertIn('Hello World', data.get('stdout', ''))
        self.assertEqual(data.get('return_code'), 0)
    
    def test_execute_failing_command(self):
        """Test /execute with a command that fails"""
        status, data = self._make_request('POST', '/execute', {
            'password': self.password,
            'command': 'exit 1'
        })
        self.assertEqual(status, 200)
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('return_code'), 1)
    
    def test_execute_command_with_stderr(self):
        """Test /execute with a command that outputs to stderr"""
        status, data = self._make_request('POST', '/execute', {
            'password': self.password,
            'command': 'echo "error message" >&2'
        })
        self.assertEqual(status, 200)
        self.assertTrue(data.get('success'))
        self.assertIn('error message', data.get('stderr', ''))
    
    def test_execute_invalid_json(self):
        """Test /execute with invalid JSON"""
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request('POST', '/execute', 'not valid json', {'Content-Type': 'application/json'})
        response = conn.getresponse()
        data = json.loads(response.read().decode('utf-8'))
        conn.close()
        
        self.assertEqual(response.status, 400)
        self.assertIn('error', data)
    
    def test_execute_empty_body(self):
        """Test /execute with empty body"""
        status, data = self._make_request('POST', '/execute', None)
        self.assertEqual(status, 400)
        self.assertIn('error', data)
    
    def test_run_script_with_temp_file(self):
        """Test /run_script with a temporary script file"""
        # Create a temporary script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Script output"\n')
            f.write('exit 0\n')
            script_path = f.name
        
        try:
            # Make script executable
            os.chmod(script_path, 0o755)
            
            status, data = self._make_request('POST', '/run_script', {
                'password': self.password,
                'script_path': script_path
            })
            
            self.assertEqual(status, 200)
            self.assertTrue(data.get('success'))
            self.assertIn('Script output', data.get('stdout', ''))
            self.assertEqual(data.get('return_code'), 0)
        finally:
            # Clean up
            os.unlink(script_path)
    
    def test_run_script_with_args(self):
        """Test /run_script with arguments"""
        # Create a temporary script that uses arguments
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Arg1: $1"\n')
            f.write('echo "Arg2: $2"\n')
            script_path = f.name
        
        try:
            os.chmod(script_path, 0o755)
            
            status, data = self._make_request('POST', '/run_script', {
                'password': self.password,
                'script_path': script_path,
                'args': ['hello', 'world']
            })
            
            self.assertEqual(status, 200)
            self.assertTrue(data.get('success'))
            self.assertIn('Arg1: hello', data.get('stdout', ''))
            self.assertIn('Arg2: world', data.get('stdout', ''))
        finally:
            os.unlink(script_path)
    
    def test_run_script_with_working_dir(self):
        """Test /run_script with working directory"""
        # Create a temporary directory and script
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, 'test.sh')
            with open(script_path, 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('pwd\n')
            os.chmod(script_path, 0o755)
            
            # Create a different working directory
            workdir = tempfile.mkdtemp()
            try:
                status, data = self._make_request('POST', '/run_script', {
                    'password': self.password,
                    'script_path': script_path,
                    'working_dir': workdir
                })
                
                self.assertEqual(status, 200)
                self.assertTrue(data.get('success'))
                self.assertIn(workdir, data.get('stdout', ''))
            finally:
                os.rmdir(workdir)
    
    def test_run_script_missing_password(self):
        """Test /run_script with missing password"""
        status, data = self._make_request('POST', '/run_script', {
            'script_path': '/tmp/test.sh'
        })
        self.assertEqual(status, 401)
        self.assertIn('error', data)
    
    def test_run_script_missing_path(self):
        """Test /run_script with missing script_path"""
        status, data = self._make_request('POST', '/run_script', {
            'password': self.password
        })
        self.assertEqual(status, 400)
        self.assertIn('error', data)
    
    def test_run_script_relative_path(self):
        """Test /run_script with relative path (should fail)"""
        status, data = self._make_request('POST', '/run_script', {
            'password': self.password,
            'script_path': 'relative/path/script.sh'
        })
        self.assertEqual(status, 400)
        self.assertIn('absolute', data.get('error', '').lower())
    
    def test_run_script_nonexistent_file(self):
        """Test /run_script with non-existent file"""
        status, data = self._make_request('POST', '/run_script', {
            'password': self.password,
            'script_path': '/tmp/nonexistent_script_12345.sh'
        })
        self.assertEqual(status, 404)
        self.assertIn('error', data)
    
    def test_run_script_invalid_args_type(self):
        """Test /run_script with args as non-list"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho test\n')
            script_path = f.name
        
        try:
            os.chmod(script_path, 0o755)
            
            status, data = self._make_request('POST', '/run_script', {
                'password': self.password,
                'script_path': script_path,
                'args': 'not a list'
            })
            
            self.assertEqual(status, 400)
            self.assertIn('error', data)
        finally:
            os.unlink(script_path)
    
    def test_run_script_relative_working_dir(self):
        """Test /run_script with relative working directory (should fail)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho test\n')
            script_path = f.name
        
        try:
            os.chmod(script_path, 0o755)
            
            status, data = self._make_request('POST', '/run_script', {
                'password': self.password,
                'script_path': script_path,
                'working_dir': 'relative/dir'
            })
            
            self.assertEqual(status, 400)
            self.assertIn('absolute', data.get('error', '').lower())
        finally:
            os.unlink(script_path)
    
    def test_404_endpoint(self):
        """Test accessing non-existent endpoint"""
        status, data = self._make_request('GET', '/nonexistent')
        self.assertEqual(status, 404)
    
    def test_post_404_endpoint(self):
        """Test POST to non-existent endpoint"""
        status, data = self._make_request('POST', '/nonexistent', {
            'password': self.password
        })
        self.assertEqual(status, 404)

if __name__ == '__main__':
    unittest.main()
