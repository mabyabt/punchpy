#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import argparse
import platform
from flask import Flask, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

class PHPServerManager:
    def __init__(self, php_dir=None, port=5000):
        # Determine base paths and system details
        self.home_dir = os.path.expanduser('~')
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.php_dir = php_dir or os.path.join(self.project_dir, 'php')
        self.server_port = port
        
        # Detect operating system
        self.os_name = platform.system().lower()
        
        # Paths for virtual environment and systemd service
        self.venv_path = os.path.join(self.project_dir, 'phpserver_env')
        self.systemd_service_path = '/etc/systemd/system/phpserver.service'
        
    def check_dependencies(self):
        """Check and install required system dependencies"""
        dependencies = {
            'linux': [
                'python3-pip',
                'python3-venv',
                'php',
                'php-sqlite3',
                'apache2',
                'libapache2-mod-php'
            ],
            'darwin': [
                'python3',
                'php',
                'sqlite3'
            ]
        }
        
        try:
            if self.os_name == 'linux':
                # Detect Linux distribution
                dist = platform.linux_distribution()[0].lower()
                
                if 'ubuntu' in dist or 'debian' in dist:
                    # Update package lists
                    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                    
                    # Install dependencies
                    install_cmd = ['sudo', 'apt-get', 'install', '-y'] + dependencies['linux']
                    subprocess.run(install_cmd, check=True)
                else:
                    print(f"Unsupported Linux distribution: {dist}")
                    return False
            
            elif self.os_name == 'darwin':
                # macOS setup (using Homebrew)
                subprocess.run(['brew', 'update'], check=True)
                install_cmd = ['brew', 'install'] + dependencies['darwin']
                subprocess.run(install_cmd, check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False
        
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        try:
            # Remove existing virtual environment if it exists
            if os.path.exists(self.venv_path):
                shutil.rmtree(self.venv_path)
            
            # Create new virtual environment
            subprocess.run([sys.executable, '-m', 'venv', self.venv_path], check=True)
            
            # Upgrade pip
            pip_path = os.path.join(self.venv_path, 'bin', 'pip')
            subprocess.run([pip_path, 'install', '--upgrade', 'pip'], check=True)
            
            # Install required Python packages
            subprocess.run([
                pip_path, 'install', 
                'flask', 
                'mod_wsgi', 
                'werkzeug'
            ], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            return False
        
    def create_systemd_service(self):
        """Create systemd service file for PHP server"""
        if self.os_name != 'linux':
            print("Systemd service is only supported on Linux")
            return False
        
        service_content = f"""[Unit]
Description=PHP Clock In/Out Server
After=network.target

[Service]
Type=simple
User={os.getlogin()}
WorkingDirectory={self.project_dir}
ExecStart={os.path.join(self.venv_path, 'bin', 'python')} {os.path.abspath(__file__)} serve
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        
        try:
            # Write service file
            with open(self.systemd_service_path, 'w') as f:
                f.write(service_content)
            
            # Reload systemd, enable and start service
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'phpserver.service'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'phpserver.service'], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating systemd service: {e}")
            return False
        
    def serve_php(self):
        """Flask application to serve PHP files"""
        app = Flask(__name__)
        app.wsgi_app = ProxyFix(app.wsgi_app)

        @app.route('/')
        @app.route('/<path:filename>')
        def serve_file(filename='index.php'):
            try:
                full_path = os.path.join(self.php_dir, filename)
                
                if not os.path.isfile(full_path):
                    full_path = os.path.join(self.php_dir, 'index.php')
                
                return send_from_directory(self.php_dir, filename)
            except Exception as e:
                return f"Error serving file: {str(e)}", 500

        # Configure environment
        os.environ['PHP_FCGI_CHILDREN'] = '5'
        os.environ['PHP_FCGI_MAX_REQUESTS'] = '1000'

        # Run the server
        app.run(host='0.0.0.0', port=self.server_port, debug=True)
    
    def setup(self):
        """Complete setup process"""
        print("Starting PHP Server Setup...")
        
        # Check and install dependencies
        if not self.check_dependencies():
            print("Dependency installation failed.")
            return False
        
        # Create virtual environment
        if not self.create_virtual_environment():
            print("Virtual environment setup failed.")
            return False
        
        # Create systemd service (Linux only)
        if self.os_name == 'linux':
            if not self.create_systemd_service():
                print("Systemd service creation failed.")
                return False
        
        print("PHP Server setup completed successfully!")
        return True

def main():
    parser = argparse.ArgumentParser(description='PHP Server Management')
    parser.add_argument('action', choices=['setup', 'serve'], 
                        help='Action to perform')
    parser.add_argument('--dir', help='PHP application directory')
    parser.add_argument('--port', type=int, default=5000, 
                        help='Port to run the server (default: 5000)')
    
    args = parser.parse_args()
    
    server_manager = PHPServerManager(
        php_dir=args.dir, 
        port=args.port
    )
    
    if args.action == 'setup':
        server_manager.setup()
    elif args.action == 'serve':
        server_manager.serve_php()

if __name__ == '__main__':
    main()
