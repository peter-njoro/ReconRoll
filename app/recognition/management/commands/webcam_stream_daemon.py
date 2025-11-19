"""
Django management command to run the webcam stream daemon.
Allows starting/stopping webcam frame forwarding from Django.

Usage:
    python manage.py webcam_stream_daemon          # Start in foreground
    python manage.py webcam_stream_daemon --daemon # Start in background
    python manage.py webcam_stream_daemon --stop   # Stop background process
"""

import os
import sys
import signal
import time
import subprocess
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Manage webcam stream daemon for frame forwarding"

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Start as background daemon',
        )
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Stop the running daemon',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Check daemon status',
        )
        parser.add_argument(
            '--url',
            type=str,
            default='http://127.0.0.1:8000',
            help='Server URL for frame uploads (default: http://127.0.0.1:8000)',
        )

    def handle(self, *args, **options):
        pid_file = Path('/tmp/webcam_stream.pid')
        log_file = Path('/tmp/webcam_stream.log')

        if options['stop']:
            self.stop_daemon(pid_file)
        elif options['status']:
            self.check_status(pid_file)
        elif options['daemon']:
            self.start_daemon(pid_file, log_file, options['url'])
        else:
            self.start_foreground(options['url'])

    def start_foreground(self, server_url):
        """Run webcam stream in foreground"""
        self.stdout.write(self.style.SUCCESS('🎥 Starting webcam stream (foreground)...'))
        self.stdout.write(f'Server URL: {server_url}')
        
        # Run the webcam stream directly
        stream_script = Path(settings.BASE_DIR) / 'recognition' / 'webcam_stream.py'
        
        if not stream_script.exists():
            raise CommandError(f'webcam_stream.py not found at {stream_script}')
        
        env = os.environ.copy()
        env['FRAME_SERVER_URL'] = server_url
        
        try:
            subprocess.run(
                [sys.executable, str(stream_script)],
                env=env,
                check=True
            )
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⏹️  Stream interrupted by user'))
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Webcam stream failed: {e}')

    def start_daemon(self, pid_file, log_file, server_url):
        """Start webcam stream as background daemon"""
        # Check if already running
        if pid_file.exists():
            try:
                with open(pid_file) as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, 0)  # Check if process exists
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Daemon already running (PID: {old_pid})')
                )
                return
            except (OSError, ValueError):
                pid_file.unlink()

        self.stdout.write(self.style.SUCCESS('🎥 Starting webcam stream daemon...'))
        self.stdout.write(f'Server URL: {server_url}')
        self.stdout.write(f'Log file: {log_file}')

        stream_script = Path(settings.BASE_DIR) / 'recognition' / 'webcam_stream.py'
        
        if not stream_script.exists():
            raise CommandError(f'webcam_stream.py not found at {stream_script}')

        env = os.environ.copy()
        env['FRAME_SERVER_URL'] = server_url

        # Start process and capture PID
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                [sys.executable, str(stream_script)],
                env=env,
                stdout=log,
                stderr=log,
                start_new_session=True  # Detach from parent process
            )

        # Save PID
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))

        # Give it a moment to start
        time.sleep(1)

        # Verify it's running
        try:
            os.kill(process.pid, 0)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Daemon started successfully (PID: {process.pid})')
            )
        except OSError:
            raise CommandError('Daemon failed to start. Check logs at ' + str(log_file))

    def stop_daemon(self, pid_file):
        """Stop the running daemon"""
        if not pid_file.exists():
            self.stdout.write(self.style.WARNING('⏹️  No daemon running'))
            return

        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            
            # Verify it's stopped
            try:
                os.kill(pid, 0)
                # Still alive, force kill
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            
            pid_file.unlink()
            self.stdout.write(self.style.SUCCESS(f'✓ Daemon stopped (PID: {pid})'))
        except (ValueError, OSError) as e:
            raise CommandError(f'Failed to stop daemon: {e}')

    def check_status(self, pid_file):
        """Check if daemon is running"""
        if not pid_file.exists():
            self.stdout.write(self.style.WARNING('⏹️  No daemon running'))
            return

        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            self.stdout.write(self.style.SUCCESS(f'✓ Daemon is running (PID: {pid})'))
            
            # Try to show last log lines
            log_file = Path('/tmp/webcam_stream.log')
            if log_file.exists():
                self.stdout.write('\n📋 Recent logs:')
                with open(log_file) as f:
                    lines = f.readlines()[-10:]
                    for line in lines:
                        self.stdout.write(f'  {line.rstrip()}')
        except OSError:
            self.stdout.write(self.style.ERROR('✗ Daemon is not running'))
            pid_file.unlink()
        except ValueError:
            raise CommandError('Invalid PID file')
