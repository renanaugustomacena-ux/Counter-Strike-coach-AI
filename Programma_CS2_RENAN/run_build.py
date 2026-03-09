import os
import subprocess
import sys

# Set environment variables
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["JAVA_HOME"] = os.path.join(project_root, "tools", "jdk17")
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ.get("PATH", "")


def execute_build():
    cwd = "Programma_CS2_RENAN/apps/android_app"
    # Use the current environment's buildozer
    buildozer_path = os.path.join(project_root, "venv", "bin", "buildozer")
    if not os.path.exists(buildozer_path):
        buildozer_path = "buildozer"  # Fallback to system path

    cmd = [buildozer_path, "android", "debug"]

    print(f"Starting buildozer from {cwd}...")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e.returncode}\n{e.output}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    execute_build()
