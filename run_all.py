"""Quick start script - runs both mock API and myAgent."""

import subprocess
import sys
import time
import signal
import os


def run_server(command, name, port):
    """Run a server process."""
    print(f"Starting {name} on port {port}...")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return process


def wait_for_server(port, timeout=10):
    """Wait for server to be ready."""
    import socket

    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


def main():
    """Start mock API, myAgent, and optionally run example."""

    print("=" * 60)
    print("myAgent Quick Start")
    print("=" * 60)
    print()

    processes = []

    try:
        mock_api = run_server("python mock_api/mock_server.py", "Mock Funnel API", 8080)
        processes.append(("Mock API", mock_api))

        if not wait_for_server(8080):
            print("❌ Mock API failed to start")
            return 1
        print("✓ Mock API ready\n")

        agent = run_server("python -m app.main", "myAgent", 8000)
        processes.append(("myAgent", agent))

        if not wait_for_server(8000):
            print("❌ myAgent failed to start")
            return 1
        print("✓ myAgent ready\n")

        print("=" * 60)
        print("Services Running:")
        print("  Mock API: http://localhost:8080")
        print("  myAgent:  http://localhost:8000")
        print("=" * 60)
        print()

        if "--example" in sys.argv:
            print("Running example usage...\n")
            time.sleep(2)
            example = subprocess.run(["python", "example_usage.py"])
            return example.returncode
        else:
            print("Both services are running!")
            print("Run example: python example_usage.py")
            print("Press Ctrl+C to stop all services\n")

            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping services...")
    finally:
        for name, process in processes:
            print(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("All services stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
