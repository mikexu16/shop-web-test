# Set environment variables
export FLASK_APP=app.py
export FLASK_DEBUG=true

# Check if venv is installed
echo "Updating dependencies"
sudo apt-get update > /dev/null
sudo apt-get install -y python3.11 python3.11-venv > /dev/null

# Check if there's a venv
if ! ls $(pwd)/.venv &> /dev/null
then
    echo "Created a virtual environment"
    python3 -m venv $(pwd)/.venv
fi

echo "Activated Virtual Environment"
. .venv/bin/activate

echo "Installing or Updating Python Requirements"

pip install -r requirements.txt > /dev/null

echo "Starting app server now"
python -m flask run