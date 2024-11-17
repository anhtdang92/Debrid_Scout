# main.py
from app import create_app

# Initialize the Flask application
app = create_app()
app.debug = True

if __name__ == "__main__":
    # app.run(debug=True) # turn on debugging mode
    app.run()
