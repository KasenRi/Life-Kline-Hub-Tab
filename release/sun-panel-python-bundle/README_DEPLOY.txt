Sun-Panel Python Bundle

Files:
- web/                built frontend
- service_python/     self-contained Python backend project
- conf/conf.ini       default config
- install.sh          install Python dependencies with uv
- run.sh              start backend on port 3002

Run on another Linux machine:
1. copy this whole folder to the target machine
2. cd into the folder
3. ./install.sh
4. ./run.sh
5. open http://127.0.0.1:3002 or http://<server-ip>:3002

Default admin account:
- username: admin@sun.cc
- password: 12345678

Requirements:
- python3
- network access for dependency installation, unless you already have the needed Python packages cached
