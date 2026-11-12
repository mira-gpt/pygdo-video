"""Keep FFmpeg tied to Dog's control pipe, including on unexpected Dog exit."""
import os
import select
import subprocess
import sys


def main(command):
    if not command:
        return 2
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        while process.poll() is None:
            ready, _, _ = select.select([sys.stdin], [], [], .25)
            if ready:
                data = os.read(sys.stdin.fileno(), 1024)
                if not data or b'q' in data:
                    try:
                        process.stdin.write(b'q\n')
                        process.stdin.flush()
                    except (BrokenPipeError, OSError):
                        pass
                    try:
                        return process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        try:
                            return process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            return process.wait()
        return process.returncode
    finally:
        if process.stdin:
            process.stdin.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
