# slowroads-localhost
Locally host slowroads.io

# Setup & Run

```sh
git clone https://github.com/Simatwa/slowroads-localhost.git
cd slowroads-localhost

uv venv
.venv\Scripts\activate # Windows
# source .venv/bin/activate - *nix
uv pip install .
python -m fastapi run

```